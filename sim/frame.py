'''
Module `frame` contains `MainFrame` class which is the window to show
on the screen. `MainFrame` is a subclass of `wx.Frame`.
'''

import wx
from node.node import BaseNode
from node.draw import Drawing
import math

class MainFrame(wx.Frame):
    '''
    This is the class for the main simulation window. It is a subclass of
    `wx.Frame`.
    '''

    def __init__(self, simworld):
        '''This is the constructor.'''
        super().__init__(None, title="Simulation", size=(600,500))

        self._simworld = simworld

        self._origin_x = 0
        self._origin_y = 0
        self._scale = 1.0

        self._on_create()
        self.Centre()
        self.Show(True)

    def _on_create(self):

        self.main_panel = wx.Panel(self)
        self.map_panel = wx.Panel(self.main_panel, style=wx.SUNKEN_BORDER)
        self.control_panel = wx.Panel(self.main_panel)

        ## map panel
        self.map_panel.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.map_panel.Bind(wx.EVT_PAINT, self._on_paint)
        self.map_panel.Bind(wx.EVT_LEFT_DOWN, self._on_map_dragged)
        self.map_panel.Bind(wx.EVT_LEFT_UP, self._on_map_dragged)
        self.map_panel.Bind(wx.EVT_MOTION, self._on_map_dragged)
        self.map_panel.Bind(wx.EVT_MOUSEWHEEL, self._on_map_scaled)

        ## control panel
        self.but_speed_down = wx.Button(self.control_panel, label="<<", style=wx.BU_EXACTFIT)
        self.but_speed_one = wx.Button(self.control_panel, label="x1", style=wx.BU_EXACTFIT)
        self.but_speed_up = wx.Button(self.control_panel, label=">>", style=wx.BU_EXACTFIT)
        self.but_pause = wx.Button(self.control_panel, label="Start")
        self.but_exit = wx.Button(self.control_panel, label="Exit")
        box_control = wx.BoxSizer(wx.HORIZONTAL)
        box_control.Add(self.but_speed_down)
        box_control.Add(self.but_speed_one)
        box_control.Add(self.but_speed_up)
        box_control.AddStretchSpacer()
        box_control.Add(self.but_pause)
        box_control.Add(self.but_exit)
        self.control_panel.SetSizer(box_control)

        self.but_speed_down.Bind(wx.EVT_LEFT_UP, self._simworld.on_button_clicked)
        self.but_speed_one.Bind(wx.EVT_LEFT_UP, self._simworld.on_button_clicked)
        self.but_speed_up.Bind(wx.EVT_LEFT_UP, self._simworld.on_button_clicked)
        self.but_pause.Bind(wx.EVT_LEFT_UP, self._simworld.on_button_clicked)
        self.but_exit.Bind(wx.EVT_LEFT_UP, self._simworld.on_button_clicked)

        ## for the main layout:
        ## define two horizontal boxes for the two panels
        ## and encapsulated in a portrait box 'vbox'
        box1 = wx.BoxSizer()
        box1.Add(self.map_panel, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        box2 = wx.BoxSizer()
        box2.Add(self.control_panel, proportion=1,flag=wx.EXPAND|wx.ALL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(box1, proportion=10,flag=wx.EXPAND|wx.ALL, border=5)
        vbox.Add(box2, proportion=1,flag=wx.EXPAND|wx.ALL, border=5)
        self.main_panel.SetSizer(vbox)

        self.sbar = self.CreateStatusBar()
        self.sbar.SetStatusStyles([wx.SB_SUNKEN])
        self.update_status_bar()

    
    def _do_render(self):

        ## getting all info for the painting
        (client_width, client_height) = self.map_panel.GetClientSize()
        if self.IsDoubleBuffered():
            dc = wx.PaintDC(self.map_panel)
        else:
            dc = wx.BufferedPaintDC(self.map_panel) 
        node_list = self._simworld.get_node_list()
        background = self._simworld.get_scenario().get_background()

        ## define an inline mapping between Cartesian and Screen coordinates
        ## the Cartesian origin will locate at the leftmost mid-height of the
        ## panel client window
        def x(cartesian_x):
            return cartesian_x # no need to translate x

        def y(cartesian_y):
            return (client_height/(2*self._scale)) - cartesian_y

        dc.Clear()
        dc.SetUserScale(self._scale,self._scale)
        dc.SetLogicalOrigin(self._origin_x,self._origin_y)

        if background!=None:
            (img,img_x,img_y) = background
            dc.DrawBitmap(img, x(img_x), y(img_y))

        ## draw coverage
        for node in node_list:
            if node.is_disabled(): continue # skip disabled node

            loc = node.get("location")
            (xx,yy) = loc.get_xy()

            for drawing in node.drawing_list:
                dc.SetPen(drawing.pen)
                dc.SetBrush(drawing.brush)
                if drawing.shape==Drawing.Shape.CIRCLE:
                    rr = drawing.radius
                    dc.DrawCircle(x(xx),y(yy),rr)
                if drawing.shape==Drawing.Shape.SECTOR:
                    rr = drawing.radius
                    ww = drawing.width_angle
                    ang = drawing.pointing_angle
                    lang = 90-(ang-ww/2)
                    rang = 90-(ang+ww/2)
                    dc.DrawEllipticArc(x(xx-rr),y(yy+rr),rr*2,rr*2,lang,rang)
                    dc.DrawLine(x(xx),y(yy),x(xx+rr*math.sin(math.radians(90-lang))),
                                            y(yy+rr*math.cos(math.radians(90-lang))))
                    dc.DrawLine(x(xx),y(yy),x(xx+rr*math.sin(math.radians(90-rang))),
                                            y(yy+rr*math.cos(math.radians(90-rang))))

        ## draw connectivity
        for node in node_list:
            if node.is_disabled(): continue # skip disabled node

            loc = node.get("location")
            (x1,y1) = loc.get_xy()

            for drawing in node.drawing_list:
                dc.SetPen(drawing.pen)
                dc.SetBrush(drawing.brush)
                if drawing.shape==Drawing.Shape.LINE:
                    (x2,y2) = drawing.other_node.get("location").get_xy()
                    dc.DrawLine(x(x1),y(y1),x(x2),y(y2))

        ## draw nodes
        for node in node_list:
            if node.is_disabled(): continue # skip disabled node

            dc.SetPen(wx.Pen(node.get_color(), 2))
            dc.SetBrush(wx.Brush(node.get_color(),wx.TRANSPARENT))

            loc = node.get("location")
            (xx,yy) = loc.get_xy()

            if node.type==BaseNode.Type.BS:
                rr = 6
                x0 = xx 
                y0 = yy 
                dc.DrawCircle(x(x0),y(y0),rr)

            elif node.type==BaseNode.Type.Vehicle:
                ## retrieve the direction and convert to xy-angle
                a = node.get("mobility").get_dir().get_azimuth()
                angle = 90 - node.get("mobility").get_dir().get_azimuth()
                if angle<0: angle+=360

                rr = 8
                x0 = xx + rr*math.cos(math.radians(-angle))
                y0 = yy - rr*math.sin(math.radians(-angle))
                x1 = xx + rr*math.cos(math.radians(-(angle+140)))
                y1 = yy - rr*math.sin(math.radians(-(angle+140)))
                x2 = xx + rr*math.cos(math.radians(-(angle+220)))
                y2 = yy - rr*math.sin(math.radians(-(angle+220)))
                points = [ (x(x0), y(y0)), (x(x1), y(y1)), (x(x2), y(y2)) ]
                dc.DrawPolygon(points)


    def _on_paint(self, event):
        self._do_render()

    def _on_map_dragged(self, event):
        if event.LeftDown():
            self._mpos_before = event.GetPosition()
            self.map_panel.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        elif event.LeftUp():
            self.map_panel.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        elif event.Dragging():
            self._mpos_after = event.GetPosition()
            self._origin_x -= (self._mpos_after.x - self._mpos_before.x)/self._scale
            self._origin_y -= (self._mpos_after.y - self._mpos_before.y)/self._scale
            self._mpos_before = self._mpos_after
            self.Refresh()

    def _on_map_scaled(self, event):

        ## compute the scaling
        (x,y) = event.GetPosition().Get()
        old_scale = self._scale
        if event.GetWheelRotation()>0:
            new_scale = self._scale + 0.1
        else:
            new_scale = self._scale - 0.1
        if new_scale<0.2: return # the scaling is too small, skip

        ## execute the scaling
        self._scale = new_scale
        self._origin_x += x/old_scale - x/new_scale
        self._origin_y += (y/old_scale - y/new_scale)/2
        self.update_status_bar()
        self.Refresh()

    def update_title(self):
        '''The simulation engine should use this method to trigger an update 
        of the window frame title.
        
        This method will access the following World property:

        - World.sim.name: to retrieve the scenario name
        '''
        title = "Simulation: %s"%self._simworld.sim.name
        if self._simworld.sim.progress>0:
            title += " (%d%%)"%self._simworld.sim.progress
        self.SetTitle(title)

    def update_status_bar(self):
        '''The simulation engine should use this method to trigger an update 
        of the status bar. This should be called when the status of the 
        simulation has changed.
        
        This method will access the following World properties:

        - World.sim.progress: to retrieve the simulation progress
        - World.sim.speed: to retrieve the animation speed
        '''
        if self._simworld.sim.progress<0:
            status_text = "Running Non-Stop"
        else:
            status_text = "Progress = %d%%"%self._simworld.sim.progress
        status_text += " | "
        status_text += "Zoom = x%1.1f"%self._scale
        status_text += " | "
        status_text += "Animation Speed = x%1.1f"%self._simworld.sim.speed
        self.sbar.SetStatusText(status_text)
        self.update_title()
