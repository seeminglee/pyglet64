# Need SystemCursor and quartz

from pyglet.libs.darwin.objc_runtime import *
from systemcursor import SystemCursor

quartz = cdll.LoadLibrary(util.find_library('quartz'))

NSApplicationDidHideNotification = c_void_p.in_dll(appkit, 'NSApplicationDidHideNotification')
NSApplicationDidUnhideNotification = c_void_p.in_dll(appkit, 'NSApplicationDidUnhideNotification')

class PygletDelegate_Implementation(object):
    PygletDelegate = ObjCSubclass('NSObject', 'PygletDelegate')
    
    @PygletDelegate.initmethod('@@')
    def initWithWindow_(self, window):
        window = cast_to_pyobject(window)
        self.objc_self = send_super(self, 'init')

        if self.objc_self is not None:
            # CocoaWindow object.
            self._window = window
            send_message(window._nswindow, 'setDelegate:', self)

        # Register delegate for hide and unhide notifications so that we 
        # can dispatch the corresponding pyglet events.
        notificationCenter = send_message('NSNotificationCenter', 'defaultCenter')
        send_message(notificationCenter, 'addObserver:selector:name:object:',
                     self,
                     get_selector('applicationDidHide:'), 
                     NSApplicationDidHideNotification,
                     None)
        send_message(notificationCenter, 'addObserver:selector:name:object:',
                     self,
                     get_selector('applicationDidUnhide:'), 
                     NSApplicationDidUnhideNotification,
                     None)
        # Flag set when we pause exclusive mouse mode if window loses key status.
        self.did_pause_exclusive_mouse = False
        return self.objc_self

    @PygletDelegate.dealloc
    def dealloc(self):
        # Unregister delegate from notification center.
        notificationCenter = send_message('NSNotificationCenter', 'defaultCenter')
        send_message(notificationCenter, 'removeObserver:', self.objc_self)
        self._window = None
        send_super(self, 'dealloc')

    @PygletDelegate.method('v@')
    def applicationDidHide_(self, notification):
        self._window.dispatch_event("on_hide")
    
    @PygletDelegate.method('v@')
    def applicationDidUnhide_(self, notification):
        if self._window._is_mouse_exclusive and quartz.CGCursorIsVisible():
            # The cursor should be hidden, but for some reason it's not;
            # try to force the cursor to hide (without over-hiding).
            SystemCursor.unhide()
            SystemCursor.hide()
            pass
        self._window.dispatch_event("on_show")

    @PygletDelegate.method('B@')
    def windowShouldClose_(self, notification):
        # The method is not called if [NSWindow close] was used.
        self._window.dispatch_event("on_close")
        return False

    @PygletDelegate.method('v@')
    def windowDidMove_(self, notification):
        x, y = self._window.get_location()
        self._window.dispatch_event("on_move", x, y)

    @PygletDelegate.method('v@')
    def windowDidBecomeKey_(self, notification):
         # Restore exclusive mouse mode if it was active before we lost key status.
         if self.did_pause_exclusive_mouse:
             self._window.set_exclusive_mouse(True)
             self.did_pause_exclusive_mouse = False
             send_message(self._window._nswindow, 'setMovable:', True, argtypes=[c_bool])   # Mac OS X 10.6 
         # Restore previous mouse visibility settings.
         self._window.set_mouse_platform_visible()
         self._window.dispatch_event("on_activate")
    
    @PygletDelegate.method('v@')
    def windowDidResignKey_(self, notification):
        # Pause exclusive mouse mode if it is active.
        if self._window._is_mouse_exclusive:
            self._window.set_exclusive_mouse(False)
            self.did_pause_exclusive_mouse = True
            # We need to prevent the window from being unintentionally dragged
            # (by the call to set_mouse_position in set_exclusive_mouse) when
            # the window is reactivated by clicking on its title bar.
            send_message(self._window._nswindow, 'setMovable:', False, argtypes=[c_bool])   # Mac OS X 10.6 
        # Make sure that cursor is visible.
        self._window.set_mouse_platform_visible(True)
        self._window.dispatch_event("on_deactivate")
        
    @PygletDelegate.method('v@')
    def windowDidMiniaturize_(self, notification):
        self._window.dispatch_event("on_hide")

    @PygletDelegate.method('v@')
    def windowDidDeminiaturize_(self, notification):
        if self._window._is_mouse_exclusive and quartz.CGCursorIsVisible():
            # The cursor should be hidden, but for some reason it's not;
            # try to force the cursor to hide (without over-hiding).
            SystemCursor.unhide()
            SystemCursor.hide()
            pass
        self._window.dispatch_event("on_show")

    @PygletDelegate.method('v@')
    def windowDidExpose_(self,  notification):
        self._window.dispatch_event("on_expose")

    @PygletDelegate.method('v@')
    def terminate_(self, sender):
        NSApp = send_message('NSApplication', 'sharedApplication')
        send_message(NSApp, 'terminate:', self.objc_self, argtypes=[c_void_p])

    @PygletDelegate.method('B@')
    def validateMenuItem_(self, menuitem):
        # Disable quitting with command-q when in keyboard exclusive mode.
        if send_message(menuitem, 'action') == get_selector('terminate:'):
            return not self._window._is_keyboard_exclusive
        return True
