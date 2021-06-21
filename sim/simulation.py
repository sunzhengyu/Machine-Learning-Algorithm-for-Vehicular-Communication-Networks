'''
Module `simulation` is the main simulation module. It contains 
a `World` class that carries out the event driven simulation and 
simulation animation.
'''

import time
import sim.scenario as scenario
from sim.frame import MainFrame
from node.node import BaseNode
from node.draw import Drawing
from sim.event import Event
import wx

class _SimEngine:
    '''
    This is an event driven simulation engine. It's an internal
    class where there should be only one instance created inside the `World` object.
    
    Usage:

    - Call schedule_process() to schedule a future process.
    - Call get_time() to return the current simulation time.
    - Call process_next_event() to process the next event in the
      simulation. Use a loop to keep calling process_next_event()
      to continuingly run the simulation.
    '''

    ## constructor
    def __init__(self):
        self.time = 0 # in seconds
        self.queue = [] # the list contains tuples: (simtime, process, parameter)

    ## this is the main event driven simulation engine
    ## it takes the next event from 'event_list' to call process
    def process_next_event(self,stop_time):

        if len(self.queue)==0: return None # no more event

        idx = self.queue.index(min(self.queue, key = lambda i : i[0]))
        (simtime,process,parameter) = self.queue.pop(idx)

        self.time = simtime
        if stop_time>0 and simtime>stop_time:
            return None # over the simulation time, stop

        if parameter==None:
            process() 
        else:
            process(parameter)

        return (simtime,process,parameter)

    ## return the current simulation time
    def get_time(self) -> float:
        return self.time

    ## schedule a process to be called after some 'delay'
    def schedule_process(self,process,parameter,delay=0):
        self.queue.append((self.time+delay, process, parameter))


class World:
    '''
    This is the simulation world.

    There should only be one simulation world in a simulation. 
    It includes an event driven simulation engine.

    Note
    ----
    The simulation world can be setup and run in two simple steps:

    - Use config() to setup the simulation world.
    - Call run() to run the simulation until the stopping condition
      is met.
    '''

    def __init__(self):
        '''The constructor for World class.'''

        ## simulation runtime controls
        class C_Sim: # simulation container
            def __init__(self):
                self.END     = -1
                self.PAUSE   =  0
                self.RUNNING =  1
        self.sim = C_Sim()
        self.sim.engine = _SimEngine()
        self.sim.running = self.sim.END
        self.sim.call_delay = 0  # the time delay (in msec) to take back control from wx
                                 # if 0, sim_loop takes back control promptly
                                 #       to run user simulation
                                 # if 1, sim_loop takes back control promptly to
                                 #       do animation rendering
                                 # if >1, sim_loop takes back control from wx after
                                 #        'call_delay' duration & then do rendering
        self.sim.progress: int = -1 # in percentage, 0 to 100, or -1 for non-stop

        ## simulation configuration & their default value
        self.sim.scenario = None
        self.sim.stop = 0.0      # stop time
        self.sim.step = 0.1      # mobility step time (simulation)
        self.sim.speed = 1.0     # simulation playback speed (x times)
        self.sim.name  = "my unnamed scenario"

        ## animation controls
        class C_Ani: # animation container
            pass
        self.ani = C_Ani()
        self.ani.display = False  # show animation (T/F)?
        self.ani.step = self.sim.step / self.sim.speed # real time step
                                  # i.e. realtime between two rendering

        ## wx main
        self.wx_app = None
        self.wx_frame = None

    def config(self, sim_stop=None, sim_step=None, 
                     sim_speed=None, display_option=None, scenario=None):
        '''The function to configure the world object. 
  
        Parameters
        ----------
        sim_stop : float
            The time that the simulation stops.
        sim_step : float
            The time step (in second) that the simulator updates 
            the movement of vehicles.
        sim_speed : float
            How many times faster the simulator should run. 
            Specifying 1.0 for simulation to run in real time, >1.0 to 
            run faster than real time, <1.0 to run slower than real time.
        display_option : bool
            Whether to enable the display to see the animation. 
            Setting False to cause the simulator to run without display 
            and animation.
        scenario : an instance of extended sim.simulation.Scenario
            The scenario to simulate.
        '''          
        if scenario!=None: self.sim.scenario = scenario
        if sim_stop!=None: self.sim.stop = sim_stop
        if sim_step!=None: self.sim.step = sim_step
        if sim_speed!=None: self.sim.speed = sim_speed
        if display_option!=None: self.ani.display = display_option

    def _on_init(self):

        ## setup display (if needed)
        if self.ani.display:
            self.wx_app = wx.App()
            self.wx_frame = MainFrame(self)
            self.wx_frame.Show()
            Drawing.enabled = True # enable drawing for all nodes
        else:
            self.wx_app = wx.App(clearSigInt=False)

        ## check and setup the scenario configuration
        if self.sim.scenario==None:
            raise Exception("Error: The simulation contains no scenario")
        if not self.sim.scenario.on_create(self):
            raise Exception("Error: Scenario creation returned an error")

        ## animation control element
        self.ani.step = self.sim.step / self.sim.speed
        self.ani.last_endtime = self._get_realtime(reset=True)

    def schedule_process(self,process,parameter=None,delay=0):
        '''The function to schedule a future process to run.

        Parameters
        ----------
        process : `callback function`
            The process to be called.
        paramater : optional, default=None
            The parameter to pass to the process. If no parameter is
            speficied, the process will be called without a parameter,
            that is `process()` instead of `process(parameter)`
        delay : float, optional, default=0
            The time delay to apply before the process is called.
        '''
        self.sim.engine.schedule_process(process,parameter,delay)

    def get_sim_time(self) -> float:
        '''The function to get simulation time (in seconds).
        
        Note
        ----
        There is no reason why user simulation needs to use this method
        to obtain simulation time, since the simulation time is passed to 
        the user simulation as a parameter.
        '''
        return self.sim.engine.get_time()

    def get_node_list(self):
        '''Use this method to get a list of all nodes in the simulation.
        
        Note
        ----
        There is no reason why user simulation needs to use this method
        to obtain all nodes, since user simulation creates all nodes in the
        own scenario class and should keep a record of all nodes within 
        the scenario class.
        '''
        return BaseNode.get_node_list()

    def get_scenario(self):
        '''Use this method to get a scenario for the simulation.

        Returns
        -------
        An instance of `sim.scenario.BaseScenario` subclass
            It returns the instance of the scenario. 
        '''
        return self.sim.scenario

    def set_scenario_name(self, name):
        '''Use this method to give a name to the scenario. The name will show 
        on the window in the GUI mode.'''
        self.sim.name = name
        if self.ani.display:
            self.wx_frame.update_title()

    def is_animation_shown(self):
        '''Use this method to check if animation is turned on for this
        simulation.

        Returns
        -------
        bool
            It returns True if the animation is turned on, False otherwise.
        '''
        return self.ani.display

    def on_button_clicked(self, event):
        '''This is an event listenser published for the frame object to call
        when there is a button clicked event, and this method should implement
        the cooresponding actions.
        
        Note
        ----
        The user simulation should not use this method. It is a callback 
        designed to be triggered by a mouse button clicked event.
        '''
        ## for speed up/one/down buttons...
        if event.GetEventObject()==self.wx_frame.but_speed_up:
            if self.sim.speed>=1: self.sim.speed+=0.5
            else: self.sim.speed+=0.1
            self.ani.step = self.sim.step / self.sim.speed
            self.wx_frame.update_status_bar()
        elif event.GetEventObject()==self.wx_frame.but_speed_down:
            if self.sim.speed>=1.5: self.sim.speed-=0.5
            elif self.sim.speed>1: self.sim.speed=1
            else: self.sim.speed-=0.1
            if self.sim.speed<=0.2: self.sim.speed=0.2
            self.ani.step = self.sim.step / self.sim.speed
            self.wx_frame.update_status_bar()
        elif event.GetEventObject()==self.wx_frame.but_speed_one:
            self.sim.speed = 1
            self.ani.step = self.sim.step / self.sim.speed
            self.wx_frame.update_status_bar()
        ## for pause button...
        elif event.GetEventObject()==self.wx_frame.but_pause:
            if self.sim.running==self.sim.PAUSE:
                self.sim.running = self.sim.RUNNING
                self.wx_frame.but_pause.SetLabel("Pause")
            elif self.sim.running==self.sim.RUNNING:
                self.sim.running = self.sim.PAUSE
                self.wx_frame.but_pause.SetLabel("Resume")
        ## for exit button...
        elif event.GetEventObject()==self.wx_frame.but_exit:
            sim_state = self.sim.running
            self.sim.running = self.sim.PAUSE
            if wx.MessageBox(
                    "This will quit the simulation\nAre you sure?",
                    "Quit Simulation",
                     wx.YES_NO | wx.NO_DEFAULT, self.wx_frame)==wx.YES:
                self.sim.scenario.on_event(self.get_sim_time(),Event.SimStop())
                wx.Exit()
            self.sim.running = sim_state
        ## everything else...
        else:
            event.Skip()

    def run(self):
        '''The function to run the simulation.

        The control will remain in this function until the simulation
        has completed.
        '''          
        self._on_init()

        ## do user simulation at the beginning and schedule the next mobility event
        self.sim.scenario.on_event(self.get_sim_time(),Event.SimStart())
        self.schedule_process(self._on_mobility_event, delay=self.sim.step)

        ## run the main loop
        ## - with display, use wx's MainLoop with a callback via CallLater()
        ##   each CallLater() callback can process exactly one event
        ## - without display, run own loop non-stop
        if self.ani.display:
            self.sim.running = self.sim.PAUSE
            self._do_rendering()
            self.wx_app.MainLoop() # wx's loop
        else:
            self.sim.running = self.sim.RUNNING
            try:
                while self.sim.running!=self.sim.END: # own loop, running non-stop
                    self._sim_loop()
            except KeyboardInterrupt:
                self.sim.scenario.on_event(self.get_sim_time(),Event.SimStop())
                self.sim.running = self.sim.END
                print("\nSimulation stopped at %1.2fs"%self.get_sim_time())

        #self.on_exit()

    def _get_realtime(self, reset=False):
        if reset:
            self.sim.t0 = time.time()
        return time.time() - self.sim.t0

    def _sim_loop(self):

        ## garbage collection
        if BaseNode._num_disabled>=10:
            node_list = BaseNode.get_node_list().copy()
            for node in node_list:
                if node.is_disabled():
                    BaseNode._node_list.remove(node)
            BaseNode._num_disabled = 0
            del node_list

        ## process the next event
        if self.sim.running==self.sim.RUNNING: 
            if self.sim.engine.process_next_event(self.sim.stop)==None:
                self.sim.running = self.sim.END
                self.sim.scenario.on_event(self.get_sim_time(),Event.SimEnd())

        ## in GUI mode, we need to register the next callback so that 
        ## we can continue to process the subsequent event,
        ## otherwise, _sim_loop() won't be called
        if self.ani.display:
            if self.sim.call_delay==0: # if delay is zero...
                ## callback immediately to run this loop again
                wx.CallLater(1, self._sim_loop) 
            else:
                ## only animation rendering process will apply delay so that
                ## the animation can play at the right speed.
                ## If delay is applied, return the control back to wx for `delay` 
                ## amount of time, then call `do_rendering()` to update screen.
                wx.CallLater(self.sim.call_delay, self._do_rendering)
            if self.sim.stop>0:
                progress = min(100,int(100.0*self.get_sim_time()/self.sim.stop))
                if self.sim.progress!=progress:
                    self.sim.progress = progress
                    self.wx_frame.update_status_bar()

    def _on_mobility_event(self):

        #print("mobility process... %f (realtime=%f)"%(self.get_sim_time(),self._get_realtime()))

        ## make all nodes move for a simulation time step
        for node in self.get_node_list():
            if node.is_disabled(): continue # skip disabled node
            if node.get("mobility").do_move(self.sim.step):
                self.sim.scenario.on_event(self.get_sim_time(),Event.MobilityEnd(node))

        ## do user simulation
        self.sim.scenario.on_event(self.get_sim_time(),Event.SimMobility())

        ## schedule the next event based on 'sim_step'
        self.schedule_process(self._on_mobility_event, delay=self.sim.step)

        ## do the following for display mode only...
        if self.ani.display:

            ## apply longer delay to slow down animation based on 'ani.step'
            current_time = self._get_realtime()
            lapse_time = current_time - self.ani.last_endtime
            remaining_time = self.ani.step - lapse_time
            if remaining_time>0:
                #threading.Event().wait(remaining_time)
                #  ^we can't use wait(), it blocks MainLoop()!!!
                #   Alternatively, we use CallLater(delay) to precisely delay
                #   the animation rendering process which produces the same 
                #   effect as wait(delay)
                self.sim.call_delay = int(remaining_time*1000)
            else:
                # the following will trigger animation process next time
                self.sim.call_delay = 1 


    def _do_rendering(self):

        ## render the simulation onto the screen
        #print("aimation process... %f (realtime=%f)"%(self.get_sim_time(),self._get_realtime()))
        self.ani.last_endtime = self._get_realtime()
        self.wx_frame.Refresh()

        ## resume the simulation loop with no delay
        self.sim.call_delay = 0
        wx.CallLater(1, self._sim_loop)

