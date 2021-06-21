'''
This is an example which demonstrates a cluster of mmWave BSs serving vehicles in a 
highway (M26) scenario. The simulation run continuously. Our design and 
assumptions are:

- Vehicle Centric: Vehicle will send a hello message to collect CQI from all BSs, and 
  then choose a BS to assiciate.
- Strongest SNR: When choosing a BS to associate, the vehicle always pick the one
  with the highest CQI (i.e. strongest SNR).
- Simultaneous beams: A BS may have multiple radio heads (RHs), each RH radiates 
  a beam. The BS can use all beams at the same time, each beam can serve a vehicle.
  If, say, the BS has 3 beams, and the condition is right, the BS can turn all 
  beams active to serve 3 different vehicles at the same time.
- Interference: If a vehicle is simultaneously covered by two active beams,
  interference occurs, and the transmission during that simulation time step is 
  considered unsuccessful. We assume that the vehicle remains associated with the
  BS, but the transmission rate for that time step is zero.
'''

import wx
import operator
import argparse
import random
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
        self.has_interference = False
        self.comm = CommModule(self)

        self.curr_conn = 0
        self.connectivity = [ [None,0,0] ] # list of connections: [bs, start_time, end_time]

    def associate_bs(self,bs,time):
        self.associated_bs = bs
        bs.serving_node = self
        self.connectivity.append([bs,time,0])
        self.curr_conn += 1

    def lost_bs(self,time):
        self.associated_bs.serving_node = None
        self.associated_bs = None
        self.connectivity[self.curr_conn][2] = time

    ## draw a line to the associated BS, if any
    def show_connection(self):
        self.clear_drawing()
        if self.associated_bs!=None:
            if self.has_interference: 
                # vehicle with a BS & has interference
                self.set_color(wx.BLACK)
                self.draw_line(self.associated_bs,pen = wx.Pen(wx.BLACK,1,style=wx.PENSTYLE_SHORT_DASH))
            else:  
                # vehicle with a BS & has no interference
                self.draw_line(self.associated_bs,pen = wx.Pen(wx.BLUE,2,style=wx.PENSTYLE_SOLID))
                self.set_color(wx.BLUE)
        else:
            # vehicle without a BS association
            self.set_color(wx.RED)

####################################################################
## Scenario
####################################################################

class MyScenario(BaseScenario,DebugPrint):
    '''
    MyScenario: This is my scenario
    '''

    ## ------------------------------------------------------------
    ## This method will be called before the start of the simulation,
    ## build the simulation world here
    def on_create(self, simworld) -> bool:

        ## simulation variables
        self.simworld = simworld
        if self.simworld.is_animation_shown():
            bitmap = wx.Bitmap()
            if bitmap.LoadFile("M26.png"):
                self.set_background(bitmap,-500,225)
            else:
                print("Error loading bitmap file, no background is applied.")
        self.set_name("A busy highway (M26)")

        ## simulation setup for beam (non-overlapping)
        self.beam_radius = 80
        self.beam_num = 6     # must be an integer
        self.beam_width = 360/self.beam_num
        self.beam_pointing = 0 # 0 means north

        ## create a common channel
        freq = 2.4
        self.omni = DiscModel(freq, self.beam_radius)

        ## create sectors for BSs
        self.ch_sector = []
        for i in range(0,self.beam_num):
            angle = self.beam_pointing + i*self.beam_width
            while angle>=360: angle-=360
            sector = SectorModel(freq, self.beam_radius, self.beam_width, angle)
            self.ch_sector.append(sector)

        ## create some nodes on the north side of the highway
        bs_locs = [XY(90,50),XY(210,50),XY(340,50)] # locations
        self.bs_north = []
        for i in range(0,len(bs_locs)): # BSs on the north side
            for j in range(0,self.beam_num): # create beams for each BS
                this_id = "BS%d.%d"%(i,j)
                this_node = MyBS(simworld, this_id, bs_locs[i], channel=self.ch_sector[j])
                self.bs_north.append(this_node)

        ## create some nodes on the south side of the highway
        bs_locs = [XY(100,-50),XY(220,-50),XY(360,-50)] # locations
        self.bs_south = []
        for i in range(0,len(bs_locs)): # BSs on the south side
            for j in range(0,self.beam_num): # create beams for each BS
                this_id = "BS%d.%d"%(i,j)
                this_node = MyBS(simworld, this_id, bs_locs[i], channel=self.ch_sector[j])
                self.bs_south.append(this_node)

        ## setup vehicle info
        self.vehicle_info = {}  # list of [start location, end location]
        y = 20; space=5
        self.vehicle_info["car1"] = [XY(0,y), XY(450,y)]; y-=space
        self.vehicle_info["car2"] = [XY(0,y), XY(450,y)]; y-=space
        self.vehicle_info["car3"] = [XY(0,y), XY(450,y)]; y-=space+3
        self.vehicle_info["car4"] = [XY(450,y), XY(0,y)]; y-=space
        self.vehicle_info["car5"] = [XY(450,y), XY(0,y)]; y-=space
        self.vehicle_info["car6"] = [XY(450,y), XY(0,y)]; y-=space

        ## create the vehicles on the highway based on above info
        self.vehicles = []
        for info in self.vehicle_info:
            start_loc = self.vehicle_info[info][0]
            end_loc = self.vehicle_info[info][1]
            path = [ (random.uniform(30,60), end_loc) ]
            node = MyVehicle(simworld, id=info, channel=self.omni)
            node.set_mobility(StaticPath(start_loc=start_loc,path=path))
            self.vehicles.append(node)

        return True

    ## --------------------------------------------------------
    ## This method will be called repeatedly until the simulation
    ## is ended or stopped, perform any simulation action here
    def on_event(self, sim_time, event_obj):

        if event_obj==Event.MOBILITY_END: # a mobile node has finished its mobility?
            self.do_restart_node(sim_time,event_obj)
        elif event_obj==Event.SIM_MOBILITY: # mobility progresses a time step?
            self.do_mobility(sim_time,event_obj)

    ## end of mobility, then create a new vehicle to replace this one
    def do_restart_node(self, sim_time, event_obj):
        this_node = event_obj.info["node"] # get the node reaching end of mobility

        speed = random.uniform(30,60)                  # new speed
        start_loc = self.vehicle_info[this_node.id][0] # new start location
        end_loc = self.vehicle_info[this_node.id][1]   # new end location
        new_path = [ (speed, end_loc) ]                # build a new path
        new_node = MyVehicle(self.simworld, id=this_node.id, channel=self.omni)
        new_node.set_mobility(StaticPath(start_loc=start_loc,path=new_path))
        self.vehicles.append(new_node) # add new node to our list

        self.vehicles.remove(this_node) # remove old node from our list
        this_node.remove_from_simulation() # remove old node from the simulation

    ## Do user simulation here
    ## main task: do BS association if needed
    def do_mobility(self, sim_time, event_obj):

        all_vehicles = self.vehicles            # get all vehicles from our liist
        all_bs = self.bs_north + self.bs_south  # get all BSs from our list

        ## check vehicle connectivity with its associated BS
        for vehicle in all_vehicles:
            bs = vehicle.associated_bs
            if bs==None: continue # skip if none

            (is_successful, cqi) = vehicle.comm.send_hello_to(bs)
            if not is_successful: # lost connection
                vehicle.lost_bs(sim_time)
                self.print("at t=%1.2f, %s lost connection with %s"%(sim_time,vehicle.id,bs.id))

        ## main task: make associatiation with BS if needed
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

        ## check for interference for each vehicle
        for vehicle in all_vehicles:

            ## skip if no BS association, probably outside of BS coverage
            if vehicle.associated_bs==None: continue

            ## use hello-beacon to find which other mmWave BS also covers this vehicle
            vehicle.has_interference = False
            beacon = QualityBasedSignal(vehicle)
            bs_list = vehicle.get("transceiver").broadcast(beacon)
            for bs in bs_list:

                ## check the bs (or more specifically, the beam)
                if bs.type!=BaseNode.Type.BS: continue # skip if not BS
                if bs.serving_node==None: continue     # skip if the bs is not active
                if bs==vehicle.associated_bs: continue # skip if it's the associated BS

                ## test if this bs associated with another vehicle 
                ## can also cover this vehicle
                (is_successful, cqi) = vehicle.comm.send_hello_to(bs)
                if is_successful: 
                    vehicle.has_interference = True # if so, set interference to True

        ## draw connectivity & beam coverage on the map
        for vehicle in all_vehicles:
            vehicle.show_connection()
        for bs in all_bs:
            bs.show_coverage()


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
    args.duration = -1     # <-- hardcoding the sim duration (sec)

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

