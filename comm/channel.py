'''
Module `channel` contains an abstract `BaseChannel` class which is the base 
class for any channel in the simulation. Each `Channel` class must implement
the following abstract methods:

- can_reach(): to calculate whether a signal transmitted by a node can reach
  another node.
- do_propagation(): to modify the given signal to capture the propagated 
  signal. The modified signal should capture the quality, distortion, etc 
  depending on how detail the implementation requires.
- can_detect(): to judge whether a receiving signal can be detected and 
  received successfully.

This module provides the following classes:

- BaseChannel: an abstract base class of a transceiver.
- DiscModel: a radiation model that uses a disc model.
  When there is a transmission, the signal will radiate within a disc 
  with the origin of the disc being the transmitting source. 
  The signal will be delivered by the channel to the transceivers within the disc.
- SectorModel: a radiation model that uses a sector model. Only nodes within a sector
  can receive the signal.
'''

from abc import ABC, abstractmethod
import sim.simulation
from node.node import BaseNode

class BaseChannel(ABC):
    '''
    This is an abstract base class for a channel operation. 
    '''

    @abstractmethod
    def __init__(self, freq):
        '''This is the constructor. It must be reimplemented and super() 
        must be called.
        
        Parameters
        ----------
        freq : float
            The frequency of this channel.
        '''
        self._freq = freq
        self._property_list = {}
        self._property_list["model"] = "Unknown"

    @abstractmethod
    def can_reach(self, source, destination, signal):
        '''This method allows a node to simulate a broadcast on this channel, and
        the method returns a list of nodes that the broadcast signal can reach.

        Parameters
        ----------
        source : node.node.BaseNode subclass instance
            The transmitting node.
        destination : node.node.BaseNode subclass instance
            The receiving node.
        signal : comm.signalwave.BaseSignal subclass instance
            The signal information for the transmission.

        Returns
        -------
        bool
            Whether `source` can reach `destination` with the transmitted `signal`.
        '''
        pass

    @abstractmethod
    def do_propagation(self, source, destination, signal):
        '''This method derives the received signal sent by `source` to
        `destination`.
        This is an abstract method to be reimplemented in the subclass.

        Parameters
        ----------
        source : node.node.BaseNode subclass instance
            The node that is transmitting the signal.
        destination : node.node.BaseNode subclass instance
            The receiving node.
        signal : an instance of `comm.signalwave.BaseSignal` subclass
            The transmitted signal. This instance will be modified appropriately
            within this method. The modification describes how the signal would
            be attenuated and distorted.

        Returns
        -------
        A instance of `comm.signalwave.BaseSignal` subclass
            The received `signal` instance.
        '''
        pass

    @abstractmethod
    def can_detect(self, signal):
        '''The method checks if a signal can be detected successfully.
        
        Returns
        -------
        bool
            Return True if the signal can be detected successfully, False
            otherwise.
        '''
        pass

    def get_property(self):
        '''The method returns a dictionary containing the properties of
        this channel.

        Returns
        -------
        Dict
            The disctionary containing the properties of this channel which
            should contain a key called `model`.
        '''
        return self._property_list

    def get_freq(self):
        '''Get the carrier frequency that this channel is using.
        
        Returns
        -------
        float
            The frequency that this channel is using for transmission.
        '''
        return self._freq


class DiscModel(BaseChannel):
    '''
    This is a subclass of BaseChannel implementing a disc model for a wireless
    channel radiation.

    For this channel model, when there is a transmission,
    the signal will propagate within a disc with the origin of the disc being the
    transmitting source. The signal will be delivered by the channel to the 
    transceivers within the disc.
    '''

    def __init__(self, freq, radius:float):
        '''This is the constructor.

        Parameters
        ----------
        freq : float
            The frequency of this channel.
        radius : float
            The transmission radius.
        '''
        super().__init__(freq)
        self._radius = radius
        self._property_list["model"] = "DiscModel"
        self._property_list["radius"] = self._radius

    def can_reach(self, source, destination, signal):
        '''This method tests if a node can reach another when transmitting
        a particualr signal. See the base class for the usage.'''

        ## check transmitting frequency
        if (source.get("transceiver").get_channel_freq()!=
            destination.get("transceiver").get_channel_freq()): 
            return False # not same freq

        ## check distance
        from_loc = source.get("location")
        to_loc = destination.get("location")
        distance = from_loc.distance_to(to_loc)
        if distance>self._radius: 
            return False # too far

        return True


    def do_propagation(self, source, destination, signal):
        '''This method derives the received signal sent by `source` to
        `destination`. See the base class for the usage.'''
        from_loc = source.get("location")
        to_loc = destination.get("location")
        distance = from_loc.distance_to(to_loc)
        if distance>self._radius: # too far
            signal.quality = 0
            signal.rx_power = 0
        else:
            signal.quality = 1 - (distance/self._radius)
            signal.rx_power = signal.quality
        return signal

    def can_detect(self, signal):
        '''This method checks if a received signal can be detected successfully.
        See the base class for the usage.'''
        if signal.quality>0: 
            return True
        else:
            return False


class SectorModel(BaseChannel):
    '''
    This is a subclass of BaseChannel implementing a sector model for 
    a wireless channel radiation.

    For this channel model, when there is a transmission,
    the signal will propagate within a sector with the origin of the sector being the
    transmitting source. The signal will be delivered by the channel to the 
    transceivers within the sector. Transceivers outside of -0.5*beam_width and 
    +0.5*beam_width of the sector will not detect the signal.
    '''

    def __init__(self, freq, radius:float, beam_width=360, azimuth=0):
        '''This is the constructor.

        Parameters
        ----------
        node : an instance of node.node.BaseNode subclass
            The assocated node of this channel.
        freq : float
            The frequency of this channel.
        radius : float
            The radius of the disc in the disc model.
        beam_width : float, optional, default=360
            The beam width (in degrees) of the sector model. The default is 360 which is
            equivalent to omnidirectional setup.
        azimuth : float, optional, default=0
            The pointing direction of the beam. The default is north pointing, positive
            indicates clockwise angle from the north, negative indicates anti-clockwise.
        '''
        super().__init__(freq)
        self._radius = radius
        self._beam_width = beam_width
        self._azimuth = azimuth

        ## condition the angles to within 0 & 360
        while self._azimuth<0: self._azimuth+=360
        while self._azimuth>=360: self._azimuth-=360
        while self._beam_width<0: self._beam_width+=360
        while self._beam_width>=360: self._beam_width-=360

        self._property_list["model"] = "SectorModel"
        self._property_list["radius"] = self._radius
        self._property_list["beam width"] = self._beam_width
        self._property_list["azimuth"] = self._azimuth


    def _is_within_sector(self, angle):
        left_edge = self._azimuth - 0.5*self._beam_width
        right_edge = self._azimuth + 0.5*self._beam_width
        return ((angle>=left_edge and angle<=right_edge) or 
                (angle+360>=left_edge and angle+360<=right_edge) or  # wrap-around
                (angle-360>=left_edge and angle-360<=right_edge))    # wrap-around


    def can_reach(self, source, destination, signal):
        '''This method tests if a node can reach another when transmitting
        a particualr signal. See the base class for the usage.'''

        ## check transmitting frequency
        if (source.get("transceiver").get_channel_freq()!=
            destination.get("transceiver").get_channel_freq()): 
            return False # not same freq

        ## check distance
        source_loc = source.get("location")
        destination_loc = destination.get("location")
        distance = source_loc.distance_to(destination_loc)
        if distance>self._radius: 
            return False # too far

        ## check angle
        angle = source_loc.azimuth_to(destination_loc)
        if not self._is_within_sector(angle):
            return False

        return True


    def do_propagation(self, source, destination, signal):
        '''This method derives the received signal sent by `source` to
        `destination`. See the base class for the usage.'''

        can_detect = True
        source_loc = source.get("location")
        destination_loc = destination.get("location")
        distance = source_loc.distance_to(destination_loc)
        angle = destination_loc.azimuth_to(source_loc)

        ## check transmitting frequency
        if (source.get("transceiver").get_channel_freq()!=
            destination.get("transceiver").get_channel_freq()): 
            can_detect = False # not same freq
        ## check distance
        elif distance>self._radius: 
            can_detect = False # too far
        ## check angle
        elif not self._is_within_sector(angle):
            can_detect = False # not in the sector

        if can_detect:
            signal.quality = 1 - (distance/self._radius)
            signal.rx_power = signal.quality
        else:
            signal.quality = 0
            signal.rx_power = 0

        return signal


    def can_detect(self, signal):
        '''This method checks if a received signal can be detected successfully.
        See the base class for the usage.'''
        if signal.quality>0: 
            return True
        else:
            return False
