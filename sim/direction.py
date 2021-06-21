'''
The module `direction` provides classes to describe the direction in the
simulation world.

The module provides the following ready-to-use classes:

- Dir2D: For a flat world, use `Dir2D` class which describes an angle of a direction.
  The angle for a North pointing direction is 0 degree. The angle increases as
  the direction rotates clockwise.
- NorthDir: A constant north pointing direction.
'''

# to cope with forward declaration for type annotation
# the following works for Python 3.7+
# expect to become a default in Python 3.10
from __future__ import annotations
import math
from sim.loc import XY
from abc import ABC, abstractmethod

class DIR(ABC):
    '''
    This is an abstract class for direction. All direction classes should extend
    this class. It may have several abstract methods to be reimplemented.
    '''

    @abstractmethod
    def __init__(self, azimuth:float=0, elevation:float=0): 
        '''This is an abstract constructor to be reimplemented. 
        Subclass should call super() to create `azimuth` and `elevation` angles.'''
        self.azimuth: float = azimuth
        self.elevation: float = elevation

    @abstractmethod
    def __add__(self, other):
        '''This is operator+ to add `other`.'''
        pass

    @abstractmethod
    def __sub__(self, other):
        '''This is operator- to subtract `other`.'''
        pass

    @abstractmethod
    def clone(self):
        '''Clone a copy of this instance.'''
        pass

    @abstractmethod
    def is_within(self, other, range:float) -> bool:
        '''This function returns a bool describing if the direction of `other` is
        within a specific range of its direction.
        
        Parameters
        ----------
        other : An instance of extended DIR
            The other direction to compare with.
        range : float
            A positive real number specifying the +/- range within itself.

        Returns
        -------
        bool
            Return whether `other` is +/- range within itself.
        '''
        pass

    @abstractmethod
    def rotate_to(self, other:Dir2D):
        '''This is a method to set its direction to `other`.'''
        pass

    @abstractmethod
    def get_azimuth(self):
        '''Return the azimuth angle.'''
        pass

    @abstractmethod
    def get_elevation(self):
        '''Return the elevation angle.'''
        pass

    def set_azimuth_given(self, from_loc, to_loc):
        (x0,y0) = from_loc.get_xy()
        (x1,y1) = to_loc.get_xy()

        angle_xy = math.atan2(y1-y0,x1-x0)
        angle_xy = math.degrees(angle_xy)
        
        self.azimuth = 90 - angle_xy
        if self.azimuth<0: self.azimuth += 360

class Dir2D(DIR):
    '''
    This is a class which describes an angle of a direction in 2D.
    The angle for a North pointing direction is 0 degree. The angle increases as
    the direction rotates clockwise.
    This class has a constant elevation angle of zero.
    '''

    def __init__(self, azimuth=0):
        '''This is the constructor.
        
        Parameters
        ----------
        azimuth : float
            The azimuth angle. For a North pointing direction, the angle is 0 degree. 
            The angle increases as the direction rotates clockwise.
        '''
        super().__init__(azimuth,0)

    def __add__(self, other):
        '''This is operator+ to add `other`.'''
        return Dir2D(self.azimuth+other.azimuth)

    def __sub__(self, other):
        '''This is operator- to subtract `other`.'''
        return Dir2D(self.azimuth-other.azimuth)

    def clone(self):
        '''Clone a copy of this instance.'''
        return Dir2D(self.azimuth)

    def get_azimuth(self):
        '''Return the azimuth angle.'''
        return self.azimuth

    def get_elevation(self):
        '''Return the elevation angle.'''
        return 0

    def rotate_to(self, other:Dir2D):
        '''This is a method to set its direction to `other`.'''
        self.azimuth = other.azimuth

    def diff(self, other:Dir2D) -> float:
        '''This function returns the angle of `other` from its point of view.
        That is, what is the angle of `other` if its angle is zero.'''
        return other.azimuth - self.azimuth

    def is_within(self, other:Dir2D, range:float) -> bool:
        '''This function returns a bool describing if the direction of `other` is
        within a specific range of its direction. See description in base class 
        for detail.'''
        diff = self.diff(other)
        if diff<=0: diff = -diff
        if diff<range:
            return True
        return False


class NorthDir(Dir2D):
    '''This is a shortcut to create a fixed North pointing direction.'''
    def __init__(self):
        super().__init__()

    def clone(self):
        '''Clone a copy of this instance.'''
        return NorthDir()

    def rotate_to(self, other):
        '''The method does nothing, since this instance describes a constant 
        direction.'''
        pass
