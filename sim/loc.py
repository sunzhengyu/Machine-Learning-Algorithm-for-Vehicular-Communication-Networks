'''
The module `loc` provides classes to describe location in the
simulation world. The instance is mutatable, use `clone()` to
create a copy and make independent changes.

The module provides the following ready-to-use classes:

- XY: For a flat world, use `XY` class which describes (x,y) location 
  in Cartesian coordinate system, where `x` and `y` are integer.
- Origin: It is an origin location, that is (0,0,0) in a 3D world.
'''

# to cope with forward declaration for type annotation
# the following works for Python 3.7+
# expect to become a default in Python 3.10
from __future__ import annotations
import math
from abc import ABC, abstractmethod

class LOC(ABC):
    '''
    This is an abstract class for location. All location classes should extend
    this class. It has several abstract methods to be reimplemented.
    '''

    @abstractmethod
    def __init__(self): 
        '''This is an abstract constructor to be reimplemented. Calling to super() is 
        unneccessary.'''
        pass

    @abstractmethod
    def __add__(self, other):
        '''This is operator+ to add `other`.
        This is an abstract method which should be explicitly reimplemented.'''
        pass

    @abstractmethod
    def __sub__(self, other):
        '''This is operator- to subtract `other`.
        This is an abstract method which should be explicitly reimplemented.'''
        pass

    @abstractmethod
    def clone(self):
        '''This function returns a clone of this instance.
        This is an abstract method which should be explicitly reimplemented.'''
        pass

    @abstractmethod
    def distance_to(self, other) -> float:
        '''This function returns how far it is from `other`. This is an abstract
        method which should be explicitly reimplemented.'''
        pass

    @abstractmethod
    def move_to(self, other, fraction:float=1.0):
        '''This function returns a new location between itself and `other` where
        the new location is a `fraction` of the two locations.
        This is an abstract method which should be explicitly reimplemented.
        
        Parameters
        ----------
        other : an instance of extended LOC
            The point to move towards.
        fraction : float
            The fraction (between 0 and 1) of distance to move to. If fraction=0,
            the new location is its original location. If fraction=1, the new
            location is the location of `other`. If fraction=0.5, the new location 
            is the mid-point between the two points.

        Returns
        -------
        LOC
            The new location after making the move. Return `None` if fraction
            is not set between 0 and 1.
        '''
        pass

    @abstractmethod
    def get_xy(self):
        '''This function returns `(x,y)` tuple.'''
        pass

    @abstractmethod
    def get_xyz(self):
        '''This function returns `(x,y,z)` tuple.'''
        pass

    @abstractmethod
    def azimuth_to(self, other):
        '''This function the azimuth angle to `other` viewed from this location.'''
        pass


class XY(LOC):
    '''
    This is a location class used to describe location in `(x,y)`
    in Cartesian coordinate system, and both `x` and `y` are an integer.
    '''

    def __init__(self, x:int=0, y:int=0):
        '''This is the constructor.
        
        Parameters
        ----------
        x, y : int
            The x and y coordinates in Cartesian coordinate system.
        '''
        self.x: int = x
        self.y: int = y

    def __add__(self, other):
        '''This is operator+ to add `other`.'''
        return XY(self.x+other.x, self.y+other.y)

    def __sub__(self, other):
        '''This is operator- to subtract `other`.'''
        return XY(self.x-other.x, self.y-other.y)

    def clone(self):
        return XY(self.x,self.y)

    def get_xy(self):
        '''This function returns `(x,y)` tuple.'''
        return (self.x, self.y)

    def get_xyz(self):
        '''This function returns `(x,y,z)` tuple.'''
        return (self.x, self.y, 0)

    def distance_to(self, other:XY) -> float:
        '''This function returns how far it is from `other`.'''
        loc2 = self - other
        return float(math.sqrt(loc2.x**2 + loc2.y**2))

    def move_to(self, other:XY, fraction:float=1.0):
        '''See the description in base class for detail.'''
        if fraction>1 or fraction<0:
            return None
        self.x += int(fraction*(other.x-self.x))
        self.y += int(fraction*(other.y-self.y))

    def azimuth_to(self, other):
        '''This function the azimuth angle to `other` viewed from this location.'''
        (x0,y0) = self.get_xy()
        (x1,y1) = other.get_xy()

        angle_xy = math.atan2(y1-y0,x1-x0)
        angle_xy = math.degrees(angle_xy)
        
        azimuth = 90 - angle_xy
        if azimuth<0: azimuth += 360
        return azimuth
    

class Origin(XY):

    def __init__(self):
        super().__init__(0,0)

    def clone(self):
        return Origin()

    def move_to(self, other, fraction:float=1.0):
        pass # `Origin` can't be moved
