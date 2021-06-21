'''This is a simple example to show how a simualtion can be created within 50 lines.
'''
from sim.simulation import World
from sim.loc import XY
from sim.scenario import BaseScenario
from node.node import BaseNode
from node.mobility import Stationary, StaticPath
from comm.transceiver import Transceiver
from comm.channel import DiscModel
from comm.signalwave import QualityBasedSignal

class MyBS(BaseNode):
    '''MyBS: This is a base station design.'''
    def __init__(self, simworld, id, loc, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.BS)
        self.set_transceiver(Transceiver(self,channel))
        self.set_mobility(Stationary(loc))

class MyVehicle(BaseNode):
    '''MyVehicle: This is a vehicle design.'''
    def __init__(self, simworld, id, start_loc, path, channel):
        super().__init__(simworld, id, node_type=BaseNode.Type.Vehicle)
        self.set_transceiver(Transceiver(self,channel))
        self.set_mobility(StaticPath(start_loc,path))

class MyScenario(BaseScenario):
    '''This is MyScenario. It reimplements on_create() and on_event().'''

    def on_create(self, simworld) -> bool: # this will be called at the start
        self.set_name("A simulation in less than 50 lines")
        omni = DiscModel(freq=2.4, radius=100)
        self.my_bs = MyBS(simworld, "BS", XY(160,0), channel=omni)
        self.my_vehicle = MyVehicle(simworld, id="Vehicle", channel=omni,
                                    start_loc=XY(10,-10), path=[(60,XY(350,-10))])
        return True

    def on_event(self, sim_time, event_obj): # this will be called repeatedly
        self.my_bs.clear_drawing()
        self.my_vehicle.clear_drawing()
        beacon_message = QualityBasedSignal(self.my_bs)
        if self.my_vehicle in self.my_bs.get("transceiver").broadcast(beacon_message):
            self.my_bs.draw_circle(100)
            self.my_vehicle.draw_line(self.my_bs)

if __name__ == "__main__":
    sim = World()
    sim.config(sim_stop=5.0, sim_step=0.1, sim_speed=1.0, display_option=True, 
               scenario=MyScenario(sim))
    sim.run()