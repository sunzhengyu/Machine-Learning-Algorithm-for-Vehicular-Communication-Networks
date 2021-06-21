'''
This module contains `BaseScenario` which is an anstract base class providing 
specification to create a scenario. It contains no implementation. 
It should be extended to a subclass to describe the actual scenario.

`BaseScenario` class is designed to be extended where the extended subclass instance
should act as a container to carry entities for the simulation. 
The subclass should use it to describe how each entity appears 
in the world. Reimplement `on_create()` method to build a scenario 
in the world.
'''

from abc import ABC, abstractmethod
from node.node import BaseNode


class BaseScenario(ABC):
    '''
    This is an anstract base class providing 
    specification to create a scenario. It contains no implementation. 
    It should be extended to a subclass to describe the actual scenario.
    '''

    def __init__(self, simworld):
        '''This is the constructor.

        Parameters
        ----------
        simworld : sim.simulation.World
        It is the container where this scenario will be put to run.
        '''
        self._world = simworld
        self._background = None

    @abstractmethod
    def on_create(self) -> bool:
        '''This is an event listener which will be called when the scenario
        object is being created. The subclass should extend this method
        to create the simulation world.

        Returns
        -------
        bool
        True if the scenario is created successfully, False otherwise.
        Returning False will cause the simulation to throw a runtime error.
        '''
        return False


    @abstractmethod
    def on_event(self, sim_time, event_obj):
        '''This is an event listener which will be called when an event occurs.
        
        The simulation periodically calls this method to allow user to perform
        any user simulation for every time step of mobility. In other words,
        the simulation continuously progresses a simulation time step, freezes 
        the time and calls this method.

        A subclass must extend this method to perform any necessary user 
        simulation on the simulation world.

        Parameters
        ----------
        sim_time : float
            The simulation time that the event happens.
        event_object : sim.event.Event
            The event object describing what has happened. The user should
            check the type of the event object and handle the event accordingly.
        '''
        pass

    def set_background(self, bitmap, x, y):
        '''Set a background bitmap image for this scenario. The background
        image will be shown on the window at (x,y) position.
        
        The input is an instance of `wx.Bitmap`. To load a bitmap from a file,
        simply use `wx.Bitmap(file_name)`.
        
        Parameters
        ----------
        bitmap : wx.Bitmap
            The bitmap to use for the scenario. 
        x,y : integer
            The position to show the bitmap on the window.
        '''
        self._background = (bitmap, x, y)

    def get_background(self):
        '''Get a background bitmap image and its position to show on the 
        window.
        
        Returns
        -------
        A tuple of (bitmap:wx.Bitmap, x:int, y:int)
            The bitmap to use for the scenario, and its (x,y) position 
            on the window.
        '''       
        return self._background

    def set_name(self, name:str):
        '''Set a name for this scenario to show on the window.
        
        Parameters
        ----------
        name : str
            The name for this scenario.
        '''
        self._world.set_scenario_name(name)

    def get_world(self):
        '''It returns the `World` instance containing this scenario.

        Returns
        -------
        sim.simulation.World
            The instance of `sim.sulation.World` which contains this scenario.
        '''
        return self._world

