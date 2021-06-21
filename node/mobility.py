'''
Module `mobility` contains various classes to describe node mobility.
'''

import sim.loc as loc
from sim.direction import Dir2D, NorthDir
from abc import ABC, abstractmethod

class BaseMobility(ABC):
    '''
    This is an abstract base class for all mobility classes to extend.

    The subclass can access to several convenicent functions
    via the base class.
    '''

    @abstractmethod
    def do_move(self, time_step):
        '''Call this method to make a move over a `time_step`. This method is used
        within the simulation engine, not for user simulation.

        Note
        ----
        There is no reason why user simulation needs to use this method. Calling
        this method from the user simulation will cause undesirable outcome.

        Parameters
        ----------
        time_step : float
            The time to move forward to (in seconds).
        '''
        pass

    @abstractmethod
    def get_loc(self):
        '''This method returns the current location.

        Note
        ----
        There is no reason why user simulation needs to use this method directly. 
        User simulation should get the location of a node by making a node query 
        using, say `my_node.get("location")` method to get the location of 
        `my_node`.

        Returns
        -------
        An instance of extended sim.loc.LOC
            The current location.
        '''
        pass

    @abstractmethod
    def get_dir(self):
        '''This method returns the current direction.

        Note
        ----
        There is no reason why user simulation needs to use this method directly. 
        The direction information is needed in the animation module to draw
        the moving node.

        Returns
        -------
        An instance of extended sim.direction.DIR
            The current direction.
        '''
        pass

    @abstractmethod
    def set_dir(self, direction):
        '''This method provides a direction to this mobility model.
        
        Providing a direction to a node is needed when the node is stationary. 
        If a mobility model is used, the mobility model will override the set 
        direction, and hence using this method to set a direction is not necessary.

        Parameters
        ----------
        direction : An instance of extended sim.direction.DIR
            The direction object to use. 
        '''
        pass


class Stationary(BaseMobility):

    def __init__(self, location, direction=None):
        '''This is the constructor.
        
        Parameters
        ----------
        location : an instance of extended sim.loc.LOC
            The node that has this mobility.
        direction : an instance of extended sim.direction.DIR, optional, default=None
            The current direction. If `None` is used, it has the same behavior as 
            sim.direction.NorthDir object.
        '''
        self._location = location
        self.set_dir(direction)

    def do_move(self, time_step):
        '''This is a stationary mobility class, so calling this method 
        does nothing. See also the base class for details.'''
        pass

    def get_loc(self):
        '''See the base class for details.'''
        return self._location

    def get_dir(self):
        '''See the base class for details.'''
        return self._direction

    def set_dir(self, direction):
        '''This is a stationary class, thus explicitly setting a direction 
        is needed. If not, `None` is used which has the same behaviour of
        a north pointing direction.
        
        Parameters
        ----------
        direction : an instance of `sim.direction.DIR` subclass
            Provide a direction instance to describe the pointing direction.
        '''
        if direction==None:
            self._direction = NorthDir()
        else:
            self._direction = direction


class StaticPath(BaseMobility):

    def __init__(self, start_loc, path=[]):
        '''This is the constructor.
        
        Parameters
        ----------
        start_loc : an instance of extended sim.loc.LOC
            The starting location.
        path : a list of (speed,location) tuple
            The list containing a series of speed-location pairs describing
            the movement.
        '''
        self._path = path  # list of (speed,loc)
        self._current_point = start_loc.clone()
        self._initial_loc = start_loc.clone()
        self._current_path = -1 if len(path)==0 else 0

        self._current_dir = Dir2D(0) # default is north pointing
        self._update_dir()

    def _update_dir(self):
        if self._current_path<0: return # empty path? skip update
        if self._current_path==len(self._path): return # no more path? skip update

        from_loc = self._current_point
        (_,to_loc) = self._path[self._current_path]

        if from_loc.distance_to(to_loc)!=0: # skip if no movement
            self._current_dir.set_azimuth_given(from_loc, to_loc)

    def add_path(self, speed, loc):
        '''Use this method to append a new path to the path list. When a node
        has completed all its movements, use this method to add a new path
        for the node to start moving again.
        
        Parameters
        ----------
        speed : float
            The speed of the new path
        loc : an instance of `sim.loc.LOC` subclass
            The end point of the new path
        '''
        self._path.append((speed,loc))
        if self._current_path==-1:
            self._current_path = 0
        self._update_dir()

    def restart(self):
        '''Use this method to restart the mobility'''
        self._current_point = self._initial_loc.clone()
        self._current_path = -1 if len(self._path)==0 else 0
        self._update_dir()

    def reset_path(self, speed, loc):
        '''Use this method to clear all existing paths and add a new path without
        changing the current location. The node will forget all the past movement
        and start moving based on the new path from its current location.
        
        Parameters
        ----------
        speed : float
            The speed of the new path
        loc : an instance of `sim.loc.LOC` subclass
            The end point of the new path
        '''
        if self._path!=None:
            self._path.clear()
        self._current_path = -1
        self.add_path(speed,loc)

    def do_move(self, time_step):
        '''See the base class for details.'''

        while self._current_path<len(self._path):
            
            (speed,end_point) = self._path[self._current_path]

            distance = self._current_point.distance_to(end_point)
            time_to_endpoint = distance / speed

            if time_step<=time_to_endpoint: # within the path?
                fraction = time_step / time_to_endpoint
                self._current_point.move_to(end_point,fraction)
                break
            else:
                time_step -= time_to_endpoint
                self._current_point.move_to(end_point)
                self._current_path += 1

        if self._current_path==len(self._path):
            return True # end of mobility
        else:
            self._update_dir()
        return False # still continue to move
        

    def get_loc(self):
        '''See the base class for details.'''
        return self._current_point

    def set_dir(self, direction):
        '''The method in this class will not do anything, since the direction 
        is calculated automatically based on the moving direction.'''
        pass # do not set direction manually

    def get_dir(self):
        '''See the base class for details.'''
        if self._current_dir==None:
            return NorthDir()
        return self._current_dir
