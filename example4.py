'''
This is an example demonstrating a number of vehicles following random waypoint
mobility moving on the map which contains a number of mmWave small cell base 
stations. The simulation runs non-stop.

In this example, we use vehicle centric where vehicle will send a hello message
to collect cqi from all BSs, and then associate with the BS with the highest
cqi (i.e. strongest SNR).
'''

import wx
import operator
import argparse
import random
from argparse import Namespace, ArgumentParser
from sim.simulation import World
from sim.loc import XY
from sim.scenario import BaseScenario
from node.node import BaseNode
from node.mobility import Stationary, StaticPath
from comm.transceiver import Transceiver
from comm.channel import DiscModel, SectorModel
from comm.signalwave import QualityBasedSignal
from sim.event import Event


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
    ## return a tuple: (outcome, cqi)
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

        self.set_transceiver(Transceiver(self,channel))
        self.associated_bs = None
        self.comm = CommModule(self)

        self.connectivity = [ [None,0,0] ] # list of connections: [bs, start_time, end_time]

    def associate_bs(self,bs,time):
        self.associated_bs = bs
        bs.serving_node = self
        self.connectivity.append([bs,time,0])

    def lost_bs(self,time):
        self.associated_bs.serving_node = None
        self.associated_bs = None
        self.connectivity[len(self.connectivity)-1][2] = time
        if len(self.connectivity)>20: # keep last 20 records
            self.connectivity.pop(0) 

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

    ## This method will be called before the start of the simulation,
    ## build the simulation world here
    def on_create(self, simworld) -> bool:

        ## simulation title
        self.set_name("Densed mmWave Small Cells")

        ## simulation setup for beam
        self.beam_radius = 80
        self.beam_num = 6     # must be an integer
        self.beam_width = 360/self.beam_num
        self.beam_pointing = 0 # 0 means north

        ## simulation setup for map
        self.map_width = 500 # pixels
        self.map_height = 300 # pixels

        ## simulation setup for nodes 
        self.bs_num = 50 # number of BSs to put on the map
        self.car_num = 5 # number of vehicles to put on the map

        ## simulation setup for channel
        self.ch_freq = 2.4
        self.ch_omni = DiscModel(self.ch_freq, self.beam_radius)
        self.ch_sector = []
        for i in range(0,self.beam_num):
            angle = self.beam_pointing + i*self.beam_width
            while angle>=360: angle-=360
            sector = SectorModel(self.ch_freq, self.beam_radius, self.beam_width, angle)
            self.ch_sector.append(sector)

        ## create BSs on the map at random locations
        self.bs_nodes = []
        for i in range(0,self.bs_num):
            loc = self.get_random_loc()
            for j in range(0,self.beam_num): # create beams for each BS
                this_id = "BS%d.%d"%(i,j)
                this_node = MyBS(simworld, this_id, loc, channel=self.ch_sector[j])
                self.bs_nodes.append(this_node)

        ## create some vehicles on the map
        self.vehicles = []
        for i in range(0,self.car_num):
            path = [ (random.uniform(40,60), self.get_random_loc()) ]
            node = MyVehicle(simworld, id="Vehicle%d"%i,channel=self.ch_omni)
            node.set_mobility(StaticPath(start_loc=self.get_random_loc(),path=path))
            self.vehicles.append(node)

        return True

    ## generate a random location
    def get_random_loc(self):
        x = int(random.random() * self.map_width)
        y = int((2*random.random()-1) * (0.5*self.map_height))
        return XY(x,y)

    ## This method will be called repeatedly until the simulation is ended/stopped
    def on_event(self, sim_time, event_obj):

        if event_obj==Event.MOBILITY_END: # a mobile node has finished its mobility?
            self.do_create_path(sim_time,event_obj)
        elif event_obj==Event.SIM_MOBILITY: # mobility progresses a time step?
            self.do_mobility(sim_time,event_obj)
        elif (event_obj==Event.SIM_END
              or event_obj==Event.SIM_STOP): # end of simulation?
            self.print_statistics()

    ## create a new path for the node
    def do_create_path(self, sim_time, event_obj):
        speed = random.uniform(30,60) # random speed
        loc = self.get_random_loc()   # random location
        node = event_obj.info["node"]
        node.get("mobility").reset_path(speed,loc)

    ## Do user simulation here
    def do_mobility(self, sim_time, event_obj):

        all_vehicles = self.vehicles
        all_bs = self.bs_nodes

        ## check vehicle connectivity with its associated BS
        for vehicle in all_vehicles:
            bs = vehicle.associated_bs
            if bs==None: continue # skip if none

            (is_successful, cqi) = vehicle.comm.send_hello_to(bs)
            if not is_successful: # lost connection
                vehicle.lost_bs(sim_time)

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
                if not is_successful: continue # skip if failed, too far perhaps

                ## 2.3 append to the detection list
                detection_list.append((bs,cqi))

            ## step 3: associate with the BS with the strongest SNR, if exists
            if len(detection_list)!=0:
                bs_max = max(detection_list,key=operator.itemgetter(1))[0]
            if bs_max!=None:
                vehicle.associate_bs(bs_max,sim_time)

        ## draw connectivity & beam coverage on the map
        for vehicle in all_vehicles:
            vehicle.show_connection()
        for bs in all_bs:
            bs.show_coverage()


    ## This method prints statistics of the connectivity durations
    ## This should be called at the end of the simulation
    def print_statistics(self):

        print("\nStatistics (last 20 connected BSs and the duration):")
        all_vehicles = self.vehicles

        conn_info_all = []
        average_all = []
        for vehicle in all_vehicles: # get statistics into `conn_info_all[]`
            conn_info_each = []
            sum_duration = 0
            connection_count = 0
            for conn in vehicle.connectivity:
                if conn[0]==None: continue
                duration = conn[2]-conn[1]
                if duration<=0: continue # unfinished record (due to sim_end)
                conn_info_each.append([conn[0].id,duration])
                sum_duration += duration
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
    parser.add_argument("--duration", help="Simulation duration (in sec)", type=int, default=1)
    args: Namespace = parser.parse_args()

    ## welcome info
    print("A Simple VANET Environment. Press [^C] to quit")
    #args.nodisplay = True  # <-- hardcoding no GUI mode
    args.step = 0.1         # <-- hardcoding the mobility step time
    args.speed = 1.0        # <-- hardcoding the animation speed (times)
    args.duration = -1      # <-- hardcoding the sim duration (sec)

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

