'''
Module `transceiver` contains `Transceiver` class which interacts with 
a channel. Each transceiver must carry a `Channel`. The operations a transceiver
can do includes:

- broadcast(): to broadcast a signal from this transceiver.
- multicase(): to multicast a signal from this transceiver. This method can
  also be used for unicast.
- received_signal(): to derive a receiving signal when it is transmitted from 
  a node over the attached channel.
'''

from node.node import BaseNode

class Transceiver:
    '''
    This is a class providing functions to simulate transceiver operations.
    '''

    def __init__(self, node, channel):
        '''This is the constructor.
        
        Parameters
        ----------
        node : node.node.BaseNode subclass instance
            The node that contains the transceiver.
        channel : comm.channel.BaseChannel subclass instance
            The channel that the transceiver uses.
        '''
        self._node = node
        self._channel = channel

    def get_channel_freq(self):
        return self._channel.get_freq()

    def broadcast(self, signal):
        '''This method allows a node to simulate a broadcast on this channel, and
        the method returns a list of nodes that the broadcast signal can reach.

        Parameters
        ----------
        signal : comm.signalwave.BaseSignal subclass instance
            The signal information used to this broadcast.

        Returns
        -------
        A list of `node.node.BaseNode` subclass instances
            It returns a list of nodes that the broadcast signal can reach.
        '''
        receiver_list = []
        for node in BaseNode.get_node_list():
            if node is self._node: continue # same node? skip
            if self._channel.can_reach(self._node, node, signal):
                receiver_list.append(node)
        return receiver_list

    def multicast(self, signal, node_list):
        '''This method allows a node to simulate a multicast on this channel, and
        the method returns a list of nodes that the multicast signal can reach.
        Note that this method can be used for unicast by putting a single node
        in `to_nodes`.

        Parameters
        ----------
        signal : comm.signalwave.BaseSignal subclass instance
            The signal information used to this broadcast.
        node_list : a list of node.node.BaseNode subclass instances
            The list containing the nodes to receive the multicast signal

        Returns
        -------
        A list of `node.node.BaseNode` subclass instances
            It returns a list of nodes that the multicast signal can reach.
        '''
        receiver_list = []
        for node in node_list:
            if self._channel.can_reach(self._node, node, signal):
                receiver_list.append(node)
        return receiver_list

    def unicast(self, signal, node):
        receiver_list = self.multicast(signal, [node])
        if len(receiver_list)==0:
            return None
        return receiver_list[0]

    def can_detect(self, signal):
        if signal.rx_power>0: # threshold
            return True
        return False

    def received_signal(self, source, signal):
        '''This method derives the received signal sent by `source`.
        This is an abstract method to be reimplemented in the subclass.

        Parameters
        ----------
        source : an instance of extended `node.node.BaseNode`
            The source that is transmitting the signal.
        signal : an instance of `comm.signalwave.BaseSignal` subclass
            The transmitted signal.

        Returns
        -------
        A new instance of `comm.signalwave.BaseSignal` subclass
            The received signal.
        '''
        recv_signal = signal.copy()
        self._channel.do_propagation(source, self._node, recv_signal)
        return recv_signal


