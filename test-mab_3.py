'''
This example shows how a base station chooses a beam to serve an approaching
vehicle. The base station has two beam configurations (a long reaching but
narrow one, and a short reaching but wide one). We assume that the base 
station can only activate one beam at a time, with either configuration.
The example uses multi-armed bandit (MAB) to select the best beam to serve.
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
    MyBS: This is a base station in the VANET sim world. In our system
    a BS is a radio head, which is just a beam.
    '''
    def __init__(self, simworld, id, loc, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.BS)

        ## beam configuration variables
        self.set_transceiver(Transceiver(self,channel))
        self.channel_property = channel.get_property()
        self.comm = CommModule(self)
        self.set_mobility(Stationary(loc))

        ## beam runtime variables for service status
        self.service_node = None
        self.service_duration = 0

        ## MAB related variables
        self.total_reward = 0
        self.total_trial = 0

    def associate_vehicle(self,node,time):
        self.service_node = node
        self.service_node.associated_bs = self
        self.service_duration = 0

    def lost_vehicle(self,time):
        self.service_node.associated_bs = None
        self.service_node = None

    ## Multi-Armed Bandit: update reward after pulling this arm (i.e. this beam)
    def MAB_update_reward(self, reward):
        self.total_reward += reward
        self.total_trial += 1

    ## Multi-Armed Bandit: calculate expected reward for this arm (i.e. this beam)
    def MAB_get_average_reward(self):
        if self.total_trial==0: 
            return 0
        return self.total_reward/self.total_trial

    ## show the coverage of this BS
    def show_coverage(self):
        self.clear_drawing()
        if self.channel_property["model"]=="DiscModel":
            if self.service_node!=None:
                self.draw_circle(self.channel_property["radius"])
        else:
            pen = wx.Pen(wx.RED,2,style=wx.PENSTYLE_LONG_DASH)
            if self.service_node!=None:
                brush = wx.Brush(wx.RED,style=wx.BRUSHSTYLE_BDIAGONAL_HATCH)
            else:
                brush = wx.Brush(wx.RED,style=wx.TRANSPARENT)
            self.draw_sector(self.channel_property["radius"],
                                self.channel_property["azimuth"],
                                self.channel_property["beam width"],
                                pen, brush)
    # def show_coverage(self):
    #     self.clear_drawing()
    #     if self.channel_property["model"]=="DiscModel":
    #         if self.service_node!=None:
    #             self.draw_circle(self.channel_property["radius"])
    #     elif self.channel_property["model"]=="SectorModel":
    #         if self.channel_property["beam width"]==60:
    #             pen = wx.Pen(wx.RED,2,style=wx.PENSTYLE_LONG_DASH)
    #         else:
    #             pen = wx.Pen(wx.BLACK,4,style=wx.PENSTYLE_SHORT_DASH)
    #         if self.service_node!=None:
    #             brush = wx.Brush(wx.RED,style=wx.BRUSHSTYLE_BDIAGONAL_HATCH)
    #         else:
    #             brush = wx.Brush(wx.RED,style=wx.TRANSPARENT)
    #         self.draw_sector(self.channel_property["radius"],
    #                             self.channel_property["azimuth"],
    #                             self.channel_property["beam width"],
    #                             pen, brush)


class MyVehicle(BaseNode):
    '''
    MyVehicle: This is a transmitting node in the VANET sim world
    '''
    def __init__(self, simworld, id, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.Vehicle)

        ## vehicle configuration variables
        self.set_transceiver(Transceiver(self,channel))
        self.comm = CommModule(self)

        ## vehicle runtime variables for service status
        self.associated_bs = None

    def associate_bs(self,bs,time):
        bs.associate_vehicle(self,time)

    def lost_bs(self,time):
        self.associated_bs.lost_vehicle(time)


    ## draw a line to the associated BS, if any
    def show_connection(self):
        self.clear_drawing()
        if self.associated_bs!=None:
            self.draw_line(self.associated_bs,pen = wx.Pen(wx.BLUE,2,style=wx.PENSTYLE_SOLID))
            self.set_color(wx.BLUE)
        else:
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

        ## for statistics
        self.last_sim_time = 0

        ## simulation variables
        self.simworld = simworld
        if self.simworld.is_animation_shown():
            bitmap = wx.Bitmap()
            if bitmap.LoadFile("croydon.png"):
                self.set_background(bitmap,-500,400)
            else:
                print("Error loading bitmap file, no background is applied.")
        self.set_name("Beam selection example")

        ## define a set of sectors covering 360 degree
        class Sectors:
            def __init__(self, freq, radius, sector_number, pointing):
                self.all_beams = []
                beam_width = 360/sector_number
                for i in range(0,sector_number):
                    angle = pointing + i*beam_width
                    while angle>=360: angle-=360
                    sector = SectorModel(freq, radius, beam_width, angle)
                    self.all_beams.append(sector)

        ## create a channel
        freq = 2.4
        radius = 120
        self.omni = DiscModel(freq, radius)

        ## create some sector beams and channels
        ## - type-1: long but narrow beams
        ## - type-2: short but wide beams
        ## - `pointing` is the pointing direction of the first beam in the sector
        sector1 = Sectors(freq, radius=120,sector_number=6,pointing=0)
        # sector2 = Sectors(freq, radius=80,sector_number=3,pointing=90)

        ## create a base station on the map
        self.bs = []
        bs_locs = [XY(200,0)] # locations
        for i in range(0,len(bs_locs)): # For each BS, do the following
            j = 0
            for beam in sector1.all_beams: # add type 1 narrow beams
                this_id = "BS%d.%dN"%(i,j); j+=1
                this_node = MyBS(simworld, this_id, bs_locs[i], channel=beam)
                self.bs.append(this_node)
            j = 0
            # for beam in sector2.all_beams: # add type 2 wide beams
            #     this_id = "BS%d.%dW"%(i,j); j+=1
            #     this_node = MyBS(simworld, this_id, bs_locs[i], channel=beam)
            #     self.bs.append(this_node)

        ## create the vehicles on a site
        self.vehicles = []
        self.vehicle_start_info = {}
        self.vehicle_start_info["car1"] = [XY(200,140)]
        self.vehicle_start_info["car1_faster"] = [XY(200,140)]

        self.vehicle_start_info["car2_slower"] = [XY(200,140)]
        self.vehicle_start_info["car2"] = [XY(200,140)]
        self.vehicle_start_info["car2_faster"] = [XY(200,140)]

        self.vehicle_start_info["car3"] = [XY(180, 190)]
        self.vehicle_start_info["car3_faster"] = [XY(180, 190)]

        self.vehicle_start_info["car4"] = [XY(180, 190)]
        self.vehicle_start_info["car4_faster"] = [XY(180, 190)]
        self.vehicle_start_info["car4_inverse"] = [XY(360, 80)]
        self.vehicle_start_info["car4_inverse_faster"] = [XY(360, 80)]

        self.vehicle_start_info["car5"] = [XY(200, 130)]
        self.vehicle_start_info["car5_faster"] = [XY(200, 130)]
        self.vehicle_start_info["car5_inverse"] = [XY(60, 15)]
        self.vehicle_start_info["car5_inverse_faster"] = [XY(60, 15)]

        self.vehicle_start_info["car6"] = [XY(200, 130)]
        self.vehicle_start_info["car6_faster"] = [XY(200, 130)]
        self.vehicle_start_info["car6_inverse"] = [XY(265, -180)]
        self.vehicle_start_info["car6_inverse_faster"] = [XY(265, -180)]


        self.vehicle_path_info = {}
        self.vehicle_path_info["car1"] = [(random.uniform(20, 30), XY(230,90)),
                                          (random.uniform(20, 30), XY(255,0)),
                                          (random.uniform(20, 30), XY(240,-45)),
                                          (random.uniform(20, 30), XY(40,-240)) ]
        self.vehicle_path_info["car1_faster"] = [(random.uniform(80, 100), XY(230, 90)),
                                          (random.uniform(80, 100), XY(255, 0)),
                                          (random.uniform(80, 100), XY(240, -45)),
                                          (random.uniform(80, 100), XY(40, -240))]

        self.vehicle_path_info["car2_slower"] = [(random.uniform(20, 30), XY(230, 90)),
                                          (random.uniform(20, 30), XY(270, 105)),
                                          (random.uniform(20, 30), XY(440, 180))]
        self.vehicle_path_info["car2"] = [(random.uniform(50, 70), XY(230,90)),
                                          (random.uniform(50, 80), XY(270,105)),
                                          (random.uniform(50, 70), XY(440,180)) ]
        self.vehicle_path_info["car2_faster"] = [(random.uniform(60, 100), XY(230,90)),
                                          (random.uniform(60, 100), XY(270,105)),
                                          (random.uniform(60, 100), XY(440,180)) ]

        self.vehicle_path_info["car3"] = [(random.uniform(50, 80), XY(205, 130)),
                                          (random.uniform(50, 70), XY(100, -60)),
                                          (random.uniform(50, 80), XY(50, -150))]
        self.vehicle_path_info["car3_faster"] = [(random.uniform(60, 100), XY(205, 130)),
                                          (random.uniform(60, 100), XY(100, -60)),
                                          (random.uniform(60, 100), XY(50, -150))]

        self.vehicle_path_info["car4"] = [(random.uniform(50, 70), XY(230,90)),
                                          (random.uniform(50, 80), XY(255, -20)),
                                          (random.uniform(50, 70), XY(310, 40)),
                                          (random.uniform(50, 80), XY(360, 80))]
        self.vehicle_path_info["car4_faster"] = [(random.uniform(60, 100), XY(230,90)),
                                          (random.uniform(60, 100), XY(255, -20)),
                                          (random.uniform(60, 100), XY(310, 40)),
                                          (random.uniform(60, 100), XY(360, 80))]
        self.vehicle_path_info["car4_inverse"] = [(random.uniform(50, 70),XY(310, 40) ),
                                          (random.uniform(50, 80), XY(255, -20)),
                                          (random.uniform(50, 70), XY(230, 90)),
                                          (random.uniform(50, 80), XY(180, 190))]
        self.vehicle_path_info["car4_inverse_faster"] = [(random.uniform(60, 100),XY(310, 40) ),
                                          (random.uniform(60, 100), XY(255, -20)),
                                          (random.uniform(60, 100), XY(230, 90)),
                                          (random.uniform(60, 100), XY(180, 190))]


        self.vehicle_path_info["car5"] = [(random.uniform(50, 70), XY(130, -10)),
                                          (random.uniform(50, 80), XY(75, 10)),
                                          (random.uniform(50, 70), XY(60, 15))]
        self.vehicle_path_info["car5_faster"] = [(random.uniform(60, 100), XY(130, -10)),
                                          (random.uniform(60, 100), XY(75, 10)),
                                          (random.uniform(60, 100), XY(60, 15))]
        self.vehicle_path_info["car5_inverse"] = [(random.uniform(50, 70), XY(75, 10)),
                                          (random.uniform(50, 80), XY(130, -10)),
                                          (random.uniform(50, 70), XY(200, 130))]
        self.vehicle_path_info["car5_inverse_faster"] = [(random.uniform(60, 100), XY(75, 10)),
                                          (random.uniform(60, 100), XY(130, -10)),
                                          (random.uniform(60, 100), XY(200, 130))]

        self.vehicle_path_info["car6"] = [(random.uniform(50, 70), XY(235, 65)),
                                          (random.uniform(50, 80), XY(250, -20)),
                                          (random.uniform(50, 70), XY(225, -75)),
                                          (random.uniform(50, 80), XY(250, -130))]
        self.vehicle_path_info["car6_faster"] = [(random.uniform(60, 100), XY(235, 65)),
                                          (random.uniform(60, 100), XY(250, -20)),
                                          (random.uniform(60, 100), XY(225, -75)),
                                          (random.uniform(60, 100), XY(250, -130))]
        self.vehicle_path_info["car6_inverse"] = [(random.uniform(50, 70), XY(225, -75)),
                                          (random.uniform(50, 80), XY(250, -20)),
                                          (random.uniform(50, 70), XY(235, 65)),
                                          (random.uniform(50, 80), XY(200, 130))]
        self.vehicle_path_info["car6_inverse_faster"] = [(random.uniform(60, 100), XY(225, -75)),
                                          (random.uniform(60, 100), XY(250, -20)),
                                          (random.uniform(60, 100), XY(235, 65)),
                                          (random.uniform(60, 100), XY(200, 130))]

        for info in self.vehicle_start_info:
            self.start_loc = self.vehicle_start_info[info][0]
            self.path = self.vehicle_path_info[info]
            node = MyVehicle(simworld, id=info, channel=self.omni)
            node.set_mobility(StaticPath(start_loc=self.start_loc,path=self.path))
            self.vehicles.append(node)

        ## show all beams
        for beam in self.bs:
            beam.show_coverage()

        return True

    ## --------------------------------------------------------
    ## This method will be called repeatedly until the simulation
    ## is ended or stopped, perform any simulation action here
    def on_event(self, sim_time, event_obj):

        duration = sim_time - self.last_sim_time
        self.last_sim_time = sim_time
        if event_obj==Event.MOBILITY_END: # a mobile node has finished its mobility?
            self.do_mobility(sim_time,duration,event_obj)
            self.do_restart_node(sim_time,event_obj)
        elif event_obj==Event.SIM_MOBILITY: # mobility progresses a time step?
            self.do_mobility(sim_time,duration,event_obj)

    ## end of mobility, then create a new vehicle to replace this one
    def do_restart_node(self, sim_time, event_obj):
        this_node = event_obj.info["node"] # retrieve the node reaching end of mobility
        new_node = MyVehicle(self.simworld, id=this_node.id, channel=self.omni)
        new_node.set_mobility(StaticPath(start_loc=self.vehicle_start_info[this_node.id][0], path=self.vehicle_path_info[this_node.id]))
        self.vehicles.append(new_node) # add new node to our list

        self.vehicles.remove(this_node) # remove old node from our list
        this_node.remove_from_simulation() # remove old node from the simulation

    ## Do user simulation here
    def do_mobility(self, sim_time, duration, event_obj):

        all_vehicles = self.vehicles    # get all vehicles from our liist
        all_beams = self.bs             # get all BSs from our list
        connect_time = 0

        ## collect stats for beams for the last period
        for beam in all_beams:
            if beam.service_node!=None:
                beam.service_duration += duration

        ## check beam connectivity with its serving vehicle
        active_beam_number = 0
        for beam in all_beams:

            if beam.service_node==None: continue # skip if none
            vehicle = beam.service_node
            active_beam_number += 1 # found an active beam

            (is_successful, cqi) = vehicle.comm.send_hello_to(beam)
            if not is_successful: # can't hear from vehicle, i.e. lost connection
                ## update reward based on service duration
                ## this is a random reward due to random vehicle speed
                beam.MAB_update_reward(beam.service_duration)
                # self.print("at t = %1.2f, %s lost connection, duration time is %1.2f, "
                #            "Beam %s total connection time is %1.2f"
                #            %(sim_time, beam.service_node.id, beam.service_duration, beam.id, beam.total_reward))
                # self.print("%s current total_reward is %1.2f, current total_trail is %s, average reward is %1.2f"
                #            %(beam.id, beam.total_reward, beam.total_trial, beam.total_reward/beam.total_trial))


                beam.lost_vehicle(sim_time)
                active_beam_number -= 1 # can't count this beam as active


        ## find a vehicle to serve if bs is available (i.e. currently no active beam)
        ## in this example, we limit the service to one vehicle maxmimum
        if active_beam_number < 1:

            ## iterate all beams to find potential vehicles to serve
            ## each potential service is an `arm`
            arm_list = [] # list of available `arms` to pull in multi-armed bandit
            for beam in all_beams:

                beacon = QualityBasedSignal(beam)
                node_list = beam.get("transceiver").broadcast(beacon)
                if beam.service_node != None: continue

                for node in node_list:
                    ## check that the reachable node is a vehicle
                    if node.type!=BaseNode.Type.Vehicle: continue # skip if not vehicle
                    # if node.associated_bs!=None: continue # skip if already being served

                    ## check also it is in the coverage of the beam
                    (is_successful, cqi) = node.comm.send_hello_to(beam)
                    if not is_successful: continue # skip if failed, likely not in coverage

                    ## add this option as an `arm` to the `arm_list`
                    arm = beam
                    reward_expectation = beam.MAB_get_average_reward()
                    arm_list.append((arm, reward_expectation, node, cqi))




            ## for exploration, pick a random arm
            ## for exploitation, pick the highest expected reward arm
            selected_beam = None
            if len(arm_list)!=0:
                if sim_time<60: # do exploration in the first 200s
                    random_number = random.random()
                    if random_number > 0.1:
                        (selected_beam,_,vehicle, cqi) = random.choice(arm_list)
                        reason = "based on exploration (random pull)"
                    else:
                        for i in arm_list:
                            self.print("the %s cqi is: %1.2f" % (i[2].id, i[3]))

                        (selected_beam,_,vehicle, cqi) = max(arm_list,key=operator.itemgetter(3))
                        reason = "based on exploration (best cqi)"


                else: # do exploitation

                    (selected_beam,_,vehicle, cqi) = max(arm_list,key=operator.itemgetter(1))
                    reason = "by choosing the best arm"

                    n = len(arm_list)
                    self.print("%s final average reaward is:%1.2f " % (arm_list[0][0].id, arm_list[0][1]))
                    for i in range(1, n):
                        last = i - 1
                        last_id = arm_list[last][0].id
                        current_id = arm_list[i][0].id
                        if last_id == current_id: continue
                        self.print("%s final average reaward is:%1.2f " % (arm_list[i][0].id, arm_list[i][1]))

            if selected_beam!=None:
                selected_beam.associate_vehicle(vehicle,sim_time)
                self.print("at t=%1.2f, %s connected to %s %s"
                            %(sim_time,vehicle.id,selected_beam.id,reason))


        ## draw connectivity & beam coverage on the map
        for vehicle in all_vehicles:
            vehicle.show_connection()
        for beam in all_beams:
            beam.show_coverage()

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

