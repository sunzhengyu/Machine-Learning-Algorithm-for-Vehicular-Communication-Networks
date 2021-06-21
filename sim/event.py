'''
The module `event` provides event description.
'''

from enum import Enum, auto

class BaseEvent:
    '''This is the base event class which should not be used directly.'''

    def __init__(self, event, info={}):
        self.event = event
        self.info = info

    def __eq__(self, event):
        return self.event==event

    def get(self, information:str):
        '''This method returns additional information about the event based on 
        the input parameter.

        Parameters
        ----------
        information : str
            The information to get.

        Returns
        -------
        any
            The value of the requested information. Return `None` is no such 
            information is carried in this event.
        '''
        if information in self.info:
            return self.info[information]
        else:
            return None


class Event:
    '''
    This is a class for an event. 
    
    An event object will be passed to the user simulation to describe what
    event has happened. An event object can be checked for its type
    directly by using, for example: `event==SIM_MOBILITY`.
    '''
    SIM_NONE     = auto()
    SIM_MOBILITY = auto()
    SIM_START    = auto()
    SIM_END      = auto()
    SIM_PAUSE    = auto()
    SIM_RESUME   = auto()
    SIM_STOP     = auto()
    MOBILITY_END = auto()

    class MobilityEnd(BaseEvent):
        '''This is an event raised when a mobility of a node has reached an end.'''
        def __init__(self, node):
            super().__init__(Event.MOBILITY_END, {"node":node})

    class SimStart(BaseEvent):
        '''This is an event raised at the beginning of the simulation.'''
        def __init__(self):
            super().__init__(Event.SIM_START, {})

    class SimEnd(BaseEvent):
        '''This is an event raised when the simulation has reached an end of the
        predefined simulation duration.'''
        def __init__(self):
            super().__init__(Event.SIM_END, {})

    class SimStop(BaseEvent):
        '''This is an event raised when the user stops a running simulation.'''
        def __init__(self):
            super().__init__(Event.SIM_STOP, {})

    class SimPause(BaseEvent):
        '''This is an event raised when the simulation is paused.'''
        def __init__(self):
            super().__init__(Event.SIM_PAUSE, {})

    class SimResume(BaseEvent):
        '''This is an event raised when the simulation resumes from pausing.'''
        def __init__(self):
            super().__init__(Event.SIM_RESUME, {})

    class SimMobility(BaseEvent):
        '''This is an event raised when the simulation has progressed forward 
        a time step.'''
        def __init__(self):
            super().__init__(Event.SIM_MOBILITY, {})
