'''
This module provides several classes related to signals.

`Signal` is used to keep information about a transmission. A transmitter should
create a signal with appropriate information describing key properties of the
signal (e.g. transmit power). At the receiver, the signal is collected and
judge whether the signal is decodeable by using the channel information to
calculate the gain, BER, and others to draw the conclusion.
Therefore, `Signal` is acting as an interface for:

- the `Channel` to write the distortion information during the transmission, and
- the `Transceiver` to then reads the distortion information and decide whether the 
  received signal passes the CRC check.

Since `Signal` acts as a common interface between `Transceiver` and `Channel`, both 
classes must agree on a common data structure to describe 
the distrotion within the `Signal`. An implementation should extend 
`comm.signalwave.BaseSignal` which provides specification and some basic
properties.

In this module, the following classes are provided with some simple implementation,
they are ready to use:

- `QualityBasedSignal`: An extension of `Signal` with a single measure of the quality 
  of the transmitted wave.
'''

from abc import ABC, abstractmethod

class BaseSignal(ABC):
    '''
    This is a abstract base class for a signal. It provides specification only.
    '''

    @abstractmethod
    def __init__(self, source, tx_power=0, rx_power=0):
        '''This is the constructor. It must be reimplemented and super() must be
        called.
        
        Parameters
        ----------
        source_node : an instance of extended `comm.tranceiver.BaseTransceiver`
            To specify which transceiver is transmitting this signal.
        tx_power, rx_power : float
            The transmit and receive powers
        '''
        self.source = source  # tx source
        self.tx_power = tx_power
        self.rx_power = rx_power

    @abstractmethod
    def copy(self):
        '''This method is used to make a copy of the signal of the subclass. 
        It must be explicitly reimplemented in a subclass.'''
        pass



class QualityBasedSignal(BaseSignal):
    '''
    This is a simple implementation of signal providing a single measure of
    an overall quality of the wave transmission.
    '''

    def __init__(self, source_node, tx_power=0, rx_power=0):
        '''This is the constructor. It must be reimplemented and super() must be
        called.
        
        Parameters
        ----------
        source_node : an instance of extended `comm.tranceiver.BaseTransceiver`
            To specify which transceiver is transmitting this signal.
        '''
        super().__init__(source_node,tx_power,rx_power)
        self.quality = 0      # indicate quality

    def copy(self):
        '''See the description in the base class for more information.
        
        Returns
        -------
        comm.signalwave.QualityBasedSignal
            Return a copy of this signal.
        '''
        signal = QualityBasedSignal(self.source,self.tx_power,self.rx_power)
        signal.quality = self.quality
        return signal


