#!/usr/bin/env python

'''
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id: $'

from pyglet import app
from base import Display, Screen, ScreenMode, Canvas

from pyglet.libs.darwin import *

class CocoaDisplay(Display):

    def get_screens(self):
        return [CocoaScreen(self, ns_screen)
                for ns_screen in NSScreen.screens()]

class CocoaScreen(Screen):

    def __init__(self, display, ns_screen):
        (x, y), (width, height) = ns_screen.frame()
        super(CocoaScreen, self).__init__(display, int(x), int(y),
                                          int(width), int(height))
        self.ns_screen = ns_screen
        self.cg_display_id = self._get_cg_display_id()
        self._default_mode = CocoaScreenMode(self)

    def _get_cg_display_id(self):
        description = self.ns_screen.deviceDescription()
        screen_key = NSString.stringWithUTF8String_("NSScreenNumber")
        nsnumber = description.objectForKey_(screen_key)
        return nsnumber.unsignedIntValue()

    def get_matching_configs(self, template):
        canvas = CocoaCanvas(self.display, self)
        return template.match(canvas)

    def get_modes(self):
        return [self._default_mode]

    def get_mode(self):
        return self._default_mode

    def set_mode(self, mode):
        assert mode == self._default_mode

    def restore_mode(self):
        pass

class CocoaScreenMode(ScreenMode):

    def __init__(self, screen):
        super(CocoaScreenMode, self).__init__(screen)
        width, height = screen.ns_screen.frame().size
        self.depth = screen.ns_screen.depth()
        self.width = int(width)
        self.height = int(height)

class CocoaCanvas(Canvas):

    def __init__(self, display, screen):
        super(CocoaCanvas, self).__init__(display)
        self.screen = screen









    """
    def _install_application_event_handlers(self):
        self._carbon_event_handlers = []
        self._carbon_event_handler_refs = []

        target = carbon.GetApplicationEventTarget()

        # TODO something with a metaclass or hacky like CarbonWindow
        # to make this list extensible
        handlers = [
            (self._on_mouse_down, kEventClassMouse, kEventMouseDown),
            (self._on_apple_event, kEventClassAppleEvent, kEventAppleEvent),
            (self._on_command, kEventClassCommand, kEventProcessCommand),
        ]

        ae_handlers = [
            (self._on_ae_quit, kCoreEventClass, kAEQuitApplication),
        ]

        # Install the application-wide handlers
        for method, cls, event in handlers:
            proc = EventHandlerProcPtr(method)
            self._carbon_event_handlers.append(proc)
            upp = carbon.NewEventHandlerUPP(proc)
            types = EventTypeSpec()
            types.eventClass = cls
            types.eventKind = event
            handler_ref = EventHandlerRef()
            carbon.InstallEventHandler(
                target,
                upp,
                1,
                byref(types),
                c_void_p(),
                byref(handler_ref))
            self._carbon_event_handler_refs.append(handler_ref)

        # Install Apple event handlers
        for method, cls, event in ae_handlers:
            proc = EventHandlerProcPtr(method)
            self._carbon_event_handlers.append(proc)
            upp = carbon.NewAEEventHandlerUPP(proc)
            carbon.AEInstallEventHandler(
                cls,
                event,
                upp,
                0,
                False)

    def _on_command(self, next_handler, ev, data):
        command = HICommand()
        carbon.GetEventParameter(ev, kEventParamDirectObject,
            typeHICommand, c_void_p(), sizeof(command), c_void_p(),
            byref(command))

        if command.commandID == kHICommandQuit:
            self._on_quit()

        return noErr

    def _on_mouse_down(self, next_handler, ev, data):
        # Check for menubar hit
        position = Point()
        carbon.GetEventParameter(ev, kEventParamMouseLocation,
            typeQDPoint, c_void_p(), sizeof(position), c_void_p(),
            byref(position))
        if carbon.FindWindow(position, None) == inMenuBar:
            # Mouse down in menu bar.  MenuSelect() takes care of all
            # menu tracking and blocks until the menu is dismissed.
            # Use command events to handle actual menu item invokations.

            # This function blocks, so tell the event loop it needs to install
            # a timer.
            app.event_loop.enter_blocking()
            carbon.MenuSelect(position)
            app.event_loop.exit_blocking()

            # Menu selection has now returned.  Remove highlight from the
            # menubar.
            carbon.HiliteMenu(0)

        carbon.CallNextEventHandler(next_handler, ev)
        return noErr

    def _on_apple_event(self, next_handler, ev, data):
        # Somewhat involved way of redispatching Apple event contained
        # within a Carbon event, described in
        # http://developer.apple.com/documentation/AppleScript/
        #  Conceptual/AppleEvents/dispatch_aes_aepg/chapter_4_section_3.html

        release = False
        if carbon.IsEventInQueue(carbon.GetMainEventQueue(), ev):
            carbon.RetainEvent(ev)
            release = True
            carbon.RemoveEventFromQueue(carbon.GetMainEventQueue(), ev)

        ev_record = EventRecord()
        carbon.ConvertEventRefToEventRecord(ev, byref(ev_record))
        carbon.AEProcessAppleEvent(byref(ev_record))

        if release:
            carbon.ReleaseEvent(ev)
        
        return noErr

    def _on_ae_quit(self, ae, reply, refcon):
        self._on_quit()
        return noErr

    def _on_quit(self):
        '''Called when the user tries to quit the application.

        This is not an actual event handler, it is called in response
        to Command+Q, the Quit menu item, and the Dock context menu's Quit
        item.

        The default implementation calls `EventLoop.exit` on
        `pyglet.app.event_loop`.
        '''
        app.event_loop.exit()
    """


        #mode = CGDisplayCurrentMode(id)
        #refresh = int( CFDictionaryGetValue(mode, kCGDisplayRefreshRate) )
        #self._refresh_rate = refresh

        #self.display = display
        #rect = carbon.CGDisplayBounds(id)
        #super(CocoaScreen, self).__init__(display,
        #    int(rect.origin.x), int(rect.origin.y),
        #    int(rect.size.width), int(rect.size.height))
        #self.id = id

        #mode = carbon.CGDisplayCurrentMode(id)
        #kCGDisplayRefreshRate = create_cfstring('RefreshRate')
        #number = carbon.CFDictionaryGetValue(mode, kCGDisplayRefreshRate)
        #refresh = c_long()
        #kCFNumberLongType = 10
        #carbon.CFNumberGetValue(number, kCFNumberLongType, byref(refresh))
        #self._refresh_rate = refresh.value

    """
        modes_array = CGDisplayAvailableModes(self.id)
        n_modes_array = CFArrayGetCount(modes_array)

        modes = []
        for i in range(n_modes_array):
            mode = CFArrayGetValueAtIndex(modes_array, i)
            modes.append(CocoaScreenMode(self, mode))

        return modes

    def get_gdevice(self):
        gdevice = POINTER(None)()
        _oscheck(carbon.DMGetGDeviceByDisplayID(self.id, byref(gdevice), False))
        return gdevice

    def get_mode(self):
        mode = carbon.CGDisplayCurrentMode(self.id)
        return CocoaScreenMode(self, mode)

    def set_mode(self, mode):
        assert mode.screen is self
        if not self._initial_mode:
            self._initial_mode = self.get_mode()

        _oscheck(carbon.CGDisplayCapture(self.id))
        _oscheck(carbon.CGDisplaySwitchToMode(self.id, mode.mode))
        self.width = mode.width
        self.height = mode.height

    def restore_mode(self):
        if self._initial_mode:
            _oscheck(carbon.CGDisplaySwitchToMode(self.id, 
                                                  self._initial_mode.mode))
        _oscheck(carbon.CGDisplayRelease(self.id))

class CocoaFullScreenCanvas(Canvas):
    # XXX not used any more.
    def __init__(self, display, screen, width, height):
        super(CocoaFullScreenCanvas, self).__init__(display)
        self.screen = screen
        self.width = width
        self.height = height
    """
