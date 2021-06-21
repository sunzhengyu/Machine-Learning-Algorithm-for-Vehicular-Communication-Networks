'''
Module `node` contains an abstract `BaseNode` class which is the base class for
all communication node entities in the simulation.
'''

from node.mobility import Stationary
from node.draw import Drawing
from abc import ABC, abstractmethod
from sim.simsystem import SimSystem
from sim.direction import Dir2D


class BaseNode(ABC,Drawing):
    '''
    This is an abstract base class for all communication node entities to
    extend.

    The subclass can access to several convenicent functions
    via the base class. Each node instance should have a unique `id`
    to be identified easily. Currently, the recommended data type for
    the `id` is string.

    Attributes
    ----------
    id : node.node.BaseNode.ID
        The `id` of this node. Ideally, this should be unique for each node
        so that a lookup can always find the appropriate node instance based on the `id`.
        However, the code will not check for uniqueness.
    type : node.node.BaseNode.Type
        The `type` of this node. The type is used in the simulation to draw the node
        on the screen. Different types will be drawn differently.
    '''

    _node_list = []   # class global lookup table
    _num_disabled = 0 # to keep track how many nodes have been marked disabled

    class ID:
        '''
        The data structure for the node id. The current implementation
        uses string for the id.
        '''
        ## the container of a node id, recommended data type is a string
        ## extend/replace this class to add a different data type
        def __init__(self,id_str:str): self.id_str = str(id_str)
        def __str__(self): return self.id_str            # for debug printing
        def __eq__(self,other): return self.id_str==other.id_str # for lookup


    class Type:
        '''
        The data structure for the node type. The animation process will use the 
        type to decide how to draw the node on the screen.
        '''
        BS =  0
        '''Use it to describe a base station. A small circle will be drawn to 
        to represent a base station.'''
        Vehicle = 1
        '''Use it to describe a vehicle. A triangle will be drawn to represent 
        a vehicle.'''
        Drone = 2
        '''Use it to describe a drone. It is not implemented at the moment.'''

        def __init__(self, node_type):
            self.type = node_type

    @abstractmethod
    def __init__(self, simworld, id=None, node_type=None):
        '''This is the constructor. It must be reimplemented and 
        super() must be called.
        
        Parameters
        ----------
        simworld : sim.simulation.World
            To provide the container of the node to be initiated.
        id : node.node.BaseNode.ID, default=None
            To provide the `id` of this node.
        type : node.node.BaseNode.Type, default=None
            To specify the `type` of this node.
        '''
        ## call Drawing constructor
        Drawing.__init__(self)

        ## initialize internal variables
        self._world: Final = simworld
        self._enabled = True
        self._mobility = None
        self._transceiver = None

        ## public properties
        self.id = id    # unique id defined by user for easy lookup
        self.type = node_type

        ## put this node to the global list for easy lookup
        BaseNode._node_list.append(self)

    @staticmethod
    def get_node_list():
        '''Provide the list of all nodes.
        
        Note
        ----
        There is no reason why user simulation needs to use this method
        to obtain all nodes, since user simulation creates all nodes in the
        own scenario class and should keep a record of all nodes within 
        the scenario class.
        '''
        return BaseNode._node_list

    def remove_from_simulation(self): 
        '''This method is used to remove this node from the simulation.
        
        In the user simulation, if nodes are allocated dynamically, this method
        must be used to remove any unwanted node. Removing a node will inform 
        the simulation engine to disable it so that it will not interact with other
        nodes in the simulation world and will not be shown on the animation.

        The method does not immediately delete the node, it marks the node
        as disabled. The simulation will ignore the disabled nodes during
        the processing. In the simulation loop, when there is a substantial number
        of disabled nodes, the simulation will trigger garbage collector to 
        remove the disabled nodes from the global list.
        '''
        self._enabled = False
        BaseNode._num_disabled += 1

    def is_disabled(self):
        '''Use this method to check if a node is disabled.

        This method is used in the simulation engine. There is no reason to use it
        in the user simulation.

        Returns
        -------
        bool
            Whether the node is disabled. Disabled nodes will not appear on the
            simualtion world.
        '''
        return self._enabled==False

    def get(self, query_str:str):
        '''Query the node to retrieve corresponding information.

        The information can be queried includes:

        - "location": the current location of the node
        - "mobility": the mobility instance of the node
        - "transceiver": the transceiver instance of the node

        Parameters
        ----------
        query_str : str
            The query string. See also above.
        '''
        if query_str=="location":
            return self._mobility.get_loc()
        elif query_str=="mobility":
            return self._mobility
        elif query_str=="transceiver":
            return self._transceiver
        SimSystem.warn.message("Calling os() with an unknown query string: '%s'"%query_str)
        return None

    def set_mobility(self, mobility, direction=None):
        '''Set the `mobility` for this instance.
        
        Parameters
        ----------
        mobility : an instance of extended node.mobility.BaseMobility
            The `mobility` model for this node.
        direction : an instance of extended sim.direction.DIR, optional, default=None
            The `direction` of the node. If None is given, the default setting will
            be a constant north pointing direction.
        '''
        self._mobility = mobility
        if direction!=None:
            self._mobility.set_dir(direction)

    def set_transceiver(self, transceiver):
        '''Use this method to set a transceiver for the node. A transceiver is 
        needed for communications.

        Parameters
        ----------
        transceiver : comm.transceiver.Transceiver
            The transceiver for this node. The transceiver provides a collection
            of functions for communications.
        '''
        self._transceiver = transceiver

    def lookup(self, id:ID):
        '''Perform a lookup for the node with `id`.
        
        This method acts like a local DNS, but we use `id` instead of a DNS 
        name, and we retrieve from the global lookup table instead of via 
        network DNS query.

        Parameters
        ----------
        id : node.node.BaseNode.ID
            The `id` to lookup.

        Returns
        -------
        node.node.BaseNode
            The node instance that carries the `id`.
        '''
        found_node = None
        for node in BaseNode._node_list:
            if node.id==id:
                found_node = node
                break
        return found_node

