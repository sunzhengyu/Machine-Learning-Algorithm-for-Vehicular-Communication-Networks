'''
This is an example which demonstrates a cluster of mmWave BSs serving vehicles in a 
highway scenario. The mobility of vehicles is predefined and static in this example.
The simulation will run for 10 seconds.

In this example, we use vehicle centric where vehicle will send a hello message
to collect cqi from all BSs, and then associate with the BS with the highest
cqi (i.e. strongest SNR).
'''

import wx
import operator
import argparse
from argparse import Namespace, ArgumentParser
from sim.simulation import World
from sim.loc import XY
from sim.scenario import BaseScenario
from sim.event import Event
from node.node import BaseNode
from node.mobility import Stationary, StaticPath
from comm.transceiver import Transceiver
from comm.channel import DiscModel, SectorModel
from comm.signalwave import QualityBasedSignal


####################################################################
## Helper
####################################################################

class DebugPrint:
    def print(self, *args, **kw):
        print(*args, **kw) # comment this line out to disable debug printing
        pass

####################################################################
## Communication Module
####################################################################

class CommModule:
    def __init__(self, node):
        self._node = node

    ## send hello message, and get replied, record channel quality indicator (cqi)
    ## return a tuple: (outcome:bool, cqi:float)
    def send_hello_to(self, other):

        cqi = 0
        me = self._node

        # send hello-message
        hello_message = QualityBasedSignal(me)
        if me.get("transceiver").unicast(hello_message, other)==None:
            return (False, cqi) # signal can't reach other? return False

        # receiver replies with hello-reply
        hello_reply = QualityBasedSignal(me)
        if other.get("transceiver").unicast(hello_reply, me)==None:
            return (False, cqi) # reply can't reach me? return False

        # hello-reply can reach me, now check the signal quality
        recv_signal = me.get("transceiver").received_signal(other,hello_reply)
        if not me.get("transceiver").can_detect(recv_signal):
            return (False, cqi) # can not detect? return False

        # return cqi
        cqi = recv_signal.quality
        return (True, cqi)


####################################################################
## Nodes
####################################################################

class MyBS(BaseNode):
    '''
    MyBS: This is a base station in the VANET sim world
    '''
    def __init__(self, simworld, id, loc, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.BS)

        ## initialize some properties
        self.set_transceiver(Transceiver(self,channel))
        self.serving_node = None
        self.channel_property = channel.get_property()
        self.comm = CommModule(self)

        ## place the BS
        self.set_mobility(Stationary(loc))

    ## show the coverage of this BS
    def show_coverage(self):
        self.clear_drawing()
        if self.serving_node!=None:
            if self.channel_property["model"]=="DiscModel":
                self.draw_circle(self.channel_property["radius"])
            elif self.channel_property["model"]=="SectorModel":
                self.draw_sector(self.channel_property["radius"],
                                 self.channel_property["azimuth"],
                                 self.channel_property["beam width"])

class MyVehicle(BaseNode):
    '''
    MyVehicle: This is a transmitting node in the VANET sim world
    '''
    def __init__(self, simworld, id, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.Vehicle)

        ## initialize some properties
        self.set_transceiver(Transceiver(self,channel))
        self.associated_bs = None
        self.comm = CommModule(self)

        ## initialize some variables to collect statistics
        self.connectivity = [ [None,0,0] ] # list of connections: [bs, start_time, end_time]

    ## associate with a BS
    def associate_bs(self,bs,time):
        self.associated_bs = bs
        bs.serving_node = self
        self.connectivity.append([bs,time,0])

    ## remove BS association due to lost of connection
    def lost_bs(self,time):
        self.associated_bs.serving_node = None
        self.associated_bs = None
        self.connectivity[len(self.connectivity)-1][2] = time

    ## draw a line to the associated BS, if any
    def show_connection(self):
        self.clear_drawing()
        if self.associated_bs!=None:
            self.draw_line(self.associated_bs)
            self.set_color(wx.BLACK)
        else:
            self.set_color(wx.RED)


####################################################################
## Scenario
####################################################################

class MyScenario(BaseScenario,DebugPrint):
    '''
    MyScenario: This is my scenario
    '''

    ##---------------------------------------------------------------
    ## This method will be called before the start of the simulation,
    ## build the simulation world here
    def on_create(self, simworld) -> bool:

        ## give a name
        self.set_name("A simple example")

        ## create a common channel
        freq = 2.4
        coverage_range = 100
        beam_width = 60
        omni = DiscModel(freq, coverage_range)
        sector = [ SectorModel(freq, coverage_range, beam_width, 180-60),
                   SectorModel(freq, coverage_range, beam_width, 180),
                   SectorModel(freq, coverage_range, beam_width, 180+60) ]
        
        ## create some nodes on the map
        bs_locs = [XY(100,60),XY(160,60),XY(280,65)] # locations
        self.bs = []
        for i in range(0,len(bs_locs)): # BSs
            for j in range(0,len(sector)): # beams for each BS
                id = "BS-%d.%d"%(i+1,j+1)
                bs = MyBS(simworld, id, bs_locs[i],channel=sector[j])
                self.bs.append(bs)

        ## create some vehicles on the highway
        self.vehicles = []

        path = [ (60, XY(200,0)), (30, XY(400,0)) ]
        node = MyVehicle(simworld, id="Vehicle1",channel=omni)
        node.set_mobility(StaticPath(start_loc=XY(10,0),path=path))
        self.vehicles.append(node)

        path = [ (40, XY(150,-10)), (50, XY(10,-10)) ]
        node = MyVehicle(simworld, id="Vehicle2",channel=omni)
        node.set_mobility(StaticPath(start_loc=XY(350,-10),path=path))
        self.vehicles.append(node)

        return True

    ##-------------------------------------------------------------
    ## This method will be called repeatedly until the simulation
    ## is ended or stopped, perform any user simulation action here
    def on_event(self, sim_time, event_obj):

        all_vehicles = self.vehicles
        all_bs = self.bs

        ## check vehicle connectivity with its associated BS
        for vehicle in all_vehicles:
            bs = vehicle.associated_bs
            if bs==None: continue # skip if none

            (is_successful, cqi) = vehicle.comm.send_hello_to(bs)
            if not is_successful: # lost connection
                vehicle.lost_bs(sim_time)
                self.print("at t=%1.2f, %s lost connection with %s"%(sim_time,vehicle.id,bs.id))

        ## make associatiation with BS if needed
        for vehicle in all_vehicles:

            ## step 1: check BS association, skip if already associated
            if vehicle.associated_bs!=None: continue

            ## step 2: find strongest SNR to associate
            bs_max = None
            detection_list = []
            beacon = QualityBasedSignal(vehicle)
            bs_list = vehicle.get("transceiver").broadcast(beacon)
            for bs in bs_list:
                ## 2.1 check that the reachable node is a BS currently not serving other
                if bs.type!=BaseNode.Type.BS: continue # skip if not BS
                if bs.serving_node!=None: continue # skip if BS is already serving other

                ## 2.2 send hello message to obtain the cqi
                (is_successful, cqi) = vehicle.comm.send_hello_to(bs)
                if not is_successful: continue # skip if failed, likely not in coverage

                ## 2.3 append to the detection list
                detection_list.append((bs,cqi))

            ## step 3: associate with the BS with the strongest SNR, if exists
            if len(detection_list)!=0:
                bs_max = max(detection_list,key=operator.itemgetter(1))[0]
            if bs_max!=None:
                vehicle.associate_bs(bs_max,sim_time)
                self.print("at t=%1.2f, %s associated with %s"%(sim_time,vehicle.id,bs_max.id))

        ## draw connectivity & beam coverage on the map
        for vehicle in all_vehicles:
            vehicle.show_connection()
        for bs in all_bs:
            bs.show_coverage()

        ## print statistics at the end of the simulation
        if event_obj==Event.SIM_END:
            print("\nStatistics (connected BS=duration):")
            conn_info_all = []
            average_all = []
            for vehicle in all_vehicles: # get statistics into `conn_info_all[]`
                conn_info_each = []
                sum_duration = 0
                connection_count = 0
                for conn in vehicle.connectivity:
                    if conn[0]==None: continue
                    conn_info_each.append([conn[0].id,conn[2]-conn[1]])
                    sum_duration += conn[2]-conn[1]
                    connection_count += 1
                conn_info_all.append(conn_info_each)
                average_all.append(sum_duration/connection_count)
            def print_fixed(text):
                print("   %s%s"%(text," "*(15-len(text))),end='')
            for vehicle in all_vehicles: # line 1, heading
                print_fixed(vehicle.id)
            print("")
            max_record = 0
            for vehicle in all_vehicles: # line 2, separator
                print_fixed("-"*len(vehicle.id))
            print("")
            for record in conn_info_all: # line 3..., connection info
                if len(record)>max_record:
                    max_record = len(record)
            for idx in range(0,max_record):
                for vnode in range(0,len(conn_info_all)):
                    if idx<len(conn_info_all[vnode]):
                        print_fixed("%s=%1.2f"%(conn_info_all[vnode][idx][0],
                                                conn_info_all[vnode][idx][1]))
                    else:
                        print_fixed(" ")
                print("")
            for vehicle in all_vehicles:  # 2nd last line, separator
                print_fixed("-"*len(vehicle.id))
            print("")
            for average in average_all:   # last line, average values
                print_fixed("Mean=%1.2f"%average)
            print("")


####################################################################
## main
####################################################################

if __name__ == "__main__":

    ## command line parameters
    parser: ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--nodisplay", help="Run in no GUI mode", action="store_true")
    parser.add_argument("--step", help="Mobility step time (in sec)", type=int, default=0.2)
    parser.add_argument("--speed", help="Animation playback speed (x times)", type=float, default=1.0)
    parser.add_argument("--duration", help="Simulation duration (in sec), -1 for non-stop", type=int, default=1)
    args: Namespace = parser.parse_args()

    ## welcome info
    print("A Simple VANET Environment. Press [^C] to quit")
    #args.nodisplay = True  # <-- hardcoding no GUI mode
    args.step = 0.1         # <-- hardcoding the mobility step time
    args.speed = 1.0        # <-- hardcoding the animation speed (times)
    args.duration = 10.0     # <-- hardcoding the sim duration (sec)

    if args.nodisplay:   print("- simulation will run without animation")
    else:                print("- animation will playback at x%1.2f speed"%args.speed)
    print("- vehicles move a step every %1.2f s in simulation"%args.step)
    if args.duration>0:  print("- simulation will stop at %1.2f s"%args.duration)
    else:                print("- simulation will run non-stop")
    print("")

    ## create, setup and run the simulation
    ## note that to run a simulation, we need to create a 'scenario'
    sim = World()
    sim.config(sim_stop = args.duration, 
               sim_step = args.step, 
               sim_speed = args.speed, 
               display_option = not args.nodisplay, 
               scenario = MyScenario(sim))
    sim.run()

