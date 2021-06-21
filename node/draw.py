'''
Module `draw` contains a `Drawing` class which can used to perform drawing
for the node. Class `node.node.BaseNode` inherits `Drawing` to add the drawing
capability. `Drawing` class provides a collection of methods useful for users
to add additional drawing on the simulation map. The drawing can be used to 
differentiate node status, shows coverage of a node, connectivity of a pair
of nodes, text info beside a node, etc.
'''

import wx
import math


class Drawing:

    enabled = False
    '''This is a class global property set by the simulation. When setting to
    False indicating that the simulation is run in a non-GUI mode, the methods 
    in this class can quickly skip the operation to improve efficiency.'''

    ## data structure for shape (base class)
    class Shape:
        '''
        Some shape constants for user to draw on the screen. The user simulation
        should use the corresponding methods provided by `node.draw.Drawing` 
        to draw a shape.
        '''
        LINE = 1
        CIRCLE = 2
        SECTOR = 3

        def __init__(self, shape, pen, brush):
            self.shape = shape
            self.pen   = pen
            self.brush = brush

    ## data structure for drawing a line
    class _Line(Shape):
        def __init__(self,other_node,pen,brush):
            super().__init__(self.LINE,pen,brush)
            self.other_node = other_node
        def matched(self,other_node):
            return self.other_node==other_node

    ## data structure for drawing a circle
    class _Circle(Shape):
        def __init__(self,radius,pen,brush):
            super().__init__(self.CIRCLE,pen,brush)
            self.radius = radius
        def matched(self,radius):
            return self.radius==radius

    ## data structure for drawing a sector
    class _Sector(Shape):
        def __init__(self,radius,pointing_angle,width_angle,pen,brush):
            super().__init__(self.SECTOR,pen,brush)
            self.radius = radius
            self.pointing_angle = pointing_angle
            self.width_angle = width_angle
        def matched(self,radius,pointing_angle,width_angle):
            return (self.radius==radius and 
                    self.pointing_angle==pointing_angle and
                    self.width_angle==width_angle)

    def __init__(self):
        self.drawing_list = [] # list of shape classes to draw around this node
        self.color = wx.BLACK  # the default color to draw this node
        self.penbrush_ready = False
        self.pen_connection = None
        self.brush_connection = None
        self.pen_coverage = None
        self.brush_coverage = None

    def _set_default_penbrush(self):
        self.pen_connection = wx.Pen(wx.BLUE,1)
        self.brush_connection = wx.Brush(wx.BLUE,wx.TRANSPARENT)
        self.pen_coverage = wx.Pen(wx.RED,1)
        self.brush_coverage = wx.Brush(wx.RED,wx.TRANSPARENT)
        self.penbrush_ready = True

    def clear_drawing(self):
        '''Clear the drawing for this node.'''
        self.drawing_list.clear()

    def draw_circle(self, radius, pen=None, brush=None):
        '''Put a circle around this node where the node is the center of the circle.

        Parameters
        ----------
        radius : float
            The radius of the circle to put around the node.
        pen : wx.Pen, optional, default=None
            The pen to draw the shape. If `None` is provided, it uses the 
            predefined pen.
        brush : wx.Brush, optional, default=None
            The brush to draw the shape. If `None` is provided, 
            it uses the predefined brush.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        ## check if the drawing already exists
        is_found = False
        for drawing in self.drawing_list:
            if drawing.shape==self.Shape.CIRCLE and drawing.matched(radius):
                is_found = True
                break
        ## create a draw if not found
        if not is_found:
            if not self.penbrush_ready: self._set_default_penbrush()
            if pen==None: pen = self.pen_coverage
            if brush==None: brush = self.brush_coverage
            self.drawing_list.append(self._Circle(radius,pen,brush))


    def del_circle(self, radius):
        '''Remove an earlier added circle for this node. If there is 
        no such circle added to the node, nothing will happen.

        Parameters
        ----------
        radius : float
            The radius that the circle to be removed.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        for drawing in self.drawing_list:
            if drawing.shape==self.Shape.CIRCLE and drawing.matched(radius):
                self.drawing_list.remove(drawing)
                break

    def draw_line(self, other_node, pen=None, brush=None):
        '''Draw a line from this node to `other_node`.

        This method is useful to show a connection between this node and 
        another node. If the line already exsits, nothing will happen.

        Parameters
        ----------
        other_node : an instance of `node.node.BaseNode` subclasses
            The node where the line to draw to from this node.
        pen : wx.Pen, optional, default=None
            The pen to draw the shape. If `None` is provided, it uses the 
            predefined pen.
        brush : wx.Brush, optional, default=None
            The brush to draw the shape. If `None` is provided, 
            it uses the predefined brush.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        ## check if the drawing already exists
        is_found = False
        for drawing in self.drawing_list:
            if drawing.shape==self.Shape.LINE and drawing.matched(other_node):
                is_found = True
                break
        ## create a draw if not found
        if not is_found:
            if not self.penbrush_ready: self._set_default_penbrush()
            if pen==None: pen = self.pen_connection
            if brush==None: brush = self.brush_connection
            self.drawing_list.append(self._Line(other_node,pen,brush))

    def del_line(self, other_node):
        '''Remove an earlier added line for this node. 
        
        This method is useful to show a connection between this node and 
        another node. If there is no such line added to the node, 
        nothing will happen.

        Parameters
        ----------
        other_node : an instance of `node.node.BaseNode` subclasses
            The line that is connected to the other node. If found, this line
            will be removed from the drawing list.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        for drawing in self.drawing_list:
            if drawing.shape==self.Shape.LINE and drawing.matched(other_node):
                self.drawing_list.remove(drawing)
                break
    

    def draw_sector(self, radius, pointing_angle, width_angle, pen=None, brush=None):
        '''Draw a sector where its center is at this node, its radius is 
        `radius` its pointing angle is `pointing_angle`, its width (in degree) 
        is specified in `width_angle`.

        This method is useful to show the coverage of a beam.

        Parameters
        ----------
        radius : float
            The radius that the sector.
        pointing_angle : float
            The pointing azimuth angle of the sector (in degrees).
        width_angle : float
            The width angle of the sector (in degrees).
        pen : wx.Pen, optional, default=None
            The pen to draw the shape. If `None` is provided, it uses the 
            predefined pen.
        brush : wx.Brush, optional, default=None
            The brush to draw the shape. If `None` is provided, 
            it uses the predefined brush.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        ## check if the drawing already exists
        is_found = False
        for drawing in self.drawing_list:
            if (drawing.shape==self.Shape.SECTOR and 
                drawing.matched(radius,pointing_angle,width_angle)):
                is_found = True
                break
        ## create a draw if not found
        if not is_found:
            if not self.penbrush_ready: self._set_default_penbrush()
            if pen==None: pen = self.pen_coverage
            if brush==None: brush = self.brush_coverage
            my_drawing = self._Sector(radius,pointing_angle,width_angle,pen,brush)
            self.drawing_list.append(my_drawing)

    def del_sector(self, radius, pointing_angle, width_angle):
        '''Remove an earlier added sector drawing. If there is 
        no such sector added to the node, nothing will happen.

        Parameters
        ----------
        radius : float
            The radius that the sector to be found for removal.
        pointing_angle : float
            The pointing azimuth angle of the sector (in degrees) 
            to be found for removal.
        width_angle : float
            The width angle of the sector (in degrees)
            to be found for removal.
        '''
        if not Drawing.enabled: return # do nothing if drawing is not allowed

        for drawing in self.drawing_list:
            if (drawing.shape==self.Shape.SECTOR and 
                drawing.matched(radius,pointing_angle,width_angle)):
                self.drawing_list.remove(drawing)
                break

    def set_color(self, color):
        '''Set the color to draw for this node.
        
        Parameters
        ----------
        color : color constant defined in wx
            The color to draw.
        '''
        self.color = color

    def get_color(self):
        '''Get the color that is used to draw this node.
        
        Returns
        -------
        Color constant defined in wx
            The color for this node.
        '''
        return self.color

    def reset_color(self):
        '''Reset the color for the node to the default color of `wx.BLACK`.'''
        self.color = wx.BLACK

