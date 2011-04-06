# ----------------------------------------------------------------------------
# pyglet
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

'''
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id: $'

from ctypes import *

import pyglet
from pyglet.window import BaseWindow, WindowException
from pyglet.window import MouseCursor, DefaultMouseCursor
from pyglet.event import EventDispatcher

from pyglet.canvas.cocoa import CocoaCanvas

from pyglet.libs.darwin.objc_runtime import *
from systemcursor import SystemCursor


class CocoaMouseCursor(MouseCursor):
    drawable = False
    def __init__(self, cursorName):
        # cursorName is a string identifying one of the named default NSCursors 
        # e.g. 'pointingHandCursor', and can be sent as message to NSCursor class.
        self.cursorName = cursorName
    def set(self):
        send_message(send_message('NSCursor', self.cursorName), 'set')


import pyglet_delegate

import pyglet_textview

import pyglet_window

import pyglet_view


class CocoaWindow(BaseWindow):

    # NSWindow instance.
    _nswindow = None

    # Delegate object.
    _delegate = None
    
    # Window properties
    _minimum_size = None
    _maximum_size = None

    _is_mouse_exclusive = False
    _mouse_platform_visible = True
    _mouse_ignore_motion = False

    _is_keyboard_exclusive = False

    # Flag set during close() method.
    _was_closed = False

    # NSWindow style masks.
    _style_masks = {
        BaseWindow.WINDOW_STYLE_DEFAULT:    NSTitledWindowMask |
                                            NSClosableWindowMask |
                                            NSMiniaturizableWindowMask,
        BaseWindow.WINDOW_STYLE_DIALOG:     NSTitledWindowMask |
                                            NSClosableWindowMask,
        BaseWindow.WINDOW_STYLE_TOOL:       NSTitledWindowMask |
                                            NSClosableWindowMask | 
                                            NSUtilityWindowMask,
        BaseWindow.WINDOW_STYLE_BORDERLESS: NSBorderlessWindowMask,
    }

    def _recreate(self, changes):
        if ('context' in changes):
            self.context.set_current()
        
        if 'fullscreen' in changes:
            if not self._fullscreen:  # leaving fullscreen
                self.screen.release_display()

        self._create()

    def _create(self):
        # Create a temporary autorelease pool for this method.
        pool = alloc_init('NSAutoreleasePool')

        if self._nswindow:
            # The window is about the be recreated so destroy everything
            # associated with the old window, then destroy the window itself.
            nsview = self.canvas.nsview
            self.canvas = None
            send_message(self._nswindow, 'orderOut:', None)
            send_message(self._nswindow, 'close')
            self.context.detach()
            send_message(self._nswindow, 'release')
            self._nswindow = None
            send_message(nsview, 'release')
            send_message(self._delegate, 'release')
            self._delegate = None

        # Determine window parameters.
        content_rect = NSMakeRect(0, 0, self._width, self._height)
        WindowClass = 'PygletWindow'
        if self._fullscreen:
            style_mask = NSBorderlessWindowMask
        else:
            if self._style not in self._style_masks:
                self._style = self.WINDOW_STYLE_DEFAULT
            style_mask = self._style_masks[self._style]
            if self._resizable:
                style_mask |= NSResizableWindowMask
            if self._style == BaseWindow.WINDOW_STYLE_TOOL:
                WindowClass = 'PygletToolWindow'

        # First create an instance of our NSWindow subclass.
        self._nswindow = send_message(WindowClass, 'alloc')
        self._nswindow = send_message(self._nswindow, 'initWithContentRect:styleMask:backing:defer:',
                                      content_rect,           # contentRect
                                      style_mask,             # styleMask
                                      NSBackingStoreBuffered, # backing
                                      False,                  # defer
                                      argtypes=[NSRect, NSUInteger, NSUInteger, c_bool])

        if self._fullscreen:
            # BUG: I suspect that this doesn't do the right thing when using
            # multiple monitors (which would be to go fullscreen on the monitor
            # where the window is located).  However I've no way to test.
            blackColor = send_message('NSColor', 'blackColor')
            send_message(self._nswindow, 'setBackgroundColor:', blackColor)
            send_message(self._nswindow, 'setOpaque:', True, argtypes=[c_bool])
            self.screen.capture_display()
            send_message(self._nswindow, 'setLevel:', quartz.CGShieldingWindowLevel(), argtypes=[NSInteger])
            self.context.set_full_screen()
            self._center_fullscreen_window()
        else:
            self._set_nice_window_location()

        # Then create a view and set it as our NSWindow's content view.
        nsview = send_message('PygletView', 'alloc')
        nsview = send_message(nsview, 'initWithFrame:cocoaWindow:',
                              content_rect, self, argtypes=[NSRect, py_object])
        send_message(self._nswindow, 'setContentView:', nsview)
        send_message(self._nswindow, 'makeFirstResponder:', nsview)

        # Create a canvas with the view as its drawable and attach context to it.
        self.canvas = CocoaCanvas(self.display, self.screen, nsview)
        self.context.attach(self.canvas)

        # Configure the window.
        send_message(self._nswindow, 'setAcceptsMouseMovedEvents:', True, argtypes=[c_bool])
        send_message(self._nswindow, 'setReleasedWhenClosed:', False, argtypes=[c_bool])
        send_message(self._nswindow, 'useOptimizedDrawing:', True, argtypes=[c_bool])
        send_message(self._nswindow, 'setPreservesContentDuringLiveResize:', False, argtypes=[c_bool])

        # Set the delegate.
        self._delegate = send_message('PygletDelegate', 'alloc')
        self._delegate = send_message(self._delegate, 'initWithWindow:', self, argtypes=[py_object])

        # Configure CocoaWindow.
        self.set_caption(self._caption)
        if self._minimum_size is not None:
            self.set_minimum_size(*self._minimum_size)
        if self._maximum_size is not None:
            self.set_maximum_size(*self._maximum_size)

        self.context.update_geometry()
        self.switch_to()
        self.set_vsync(self._vsync)
        self.set_visible(self._visible)

        send_message(pool, 'drain')

    def _set_nice_window_location(self):
        # Construct a list of all visible windows that aren't us.
        visible_windows = [ win for win in pyglet.app.windows if
                            win is not self and 
                            win._nswindow and 
                            send_message(win._nswindow, 'isVisible', restype=c_bool) ]
        # If there aren't any visible windows, then center this window.
        if not visible_windows:
            send_message(self._nswindow, 'center')
        # Otherwise, cascade from last window in list.
        else:
            point = send_message(visible_windows[-1]._nswindow, 
                                 'cascadeTopLeftFromPoint:', NSZeroPoint, 
                                 restype=NSPoint, argtypes=[NSPoint])
            send_message(self._nswindow, 'cascadeTopLeftFromPoint:', point,
                         restype=NSPoint, argtypes=[NSPoint])

    def _center_fullscreen_window(self):
        # [NSWindow center] does not move the window to a true center position.
        x = int((self.screen.width - self._width)/2)
        y = int((self.screen.height - self._height)/2)
        send_message(self._nswindow, 'setFrameOrigin:', NSPoint(x, y), argtypes=[NSPoint])

    def close(self):
        # If we've already gone through this once, don't do it again.
        if self._was_closed:
            return

        # Create a temporary autorelease pool for this method.
        pool = alloc_init('NSAutoreleasePool')

        # Restore cursor visibility
        self.set_mouse_platform_visible(True)
        self.set_exclusive_mouse(False)
        self.set_exclusive_keyboard(False)

        # Remove the delegate object
        if self._delegate:
            send_message(self._nswindow, 'setDelegate:', None)
            send_message(self._delegate, 'release')
            self._delegate = None
            
        # Remove window from display and remove its view.
        if self._nswindow:
            send_message(self._nswindow, 'orderOut:', None)
            send_message(self._nswindow, 'setContentView:', None)
            send_message(self._nswindow, 'close')

        # Restore screen mode. This also releases the display
        # if it was captured for fullscreen mode.
        self.screen.restore_mode()

        # Remove view from canvas and then remove canvas.
        if self.canvas:
            send_message(self.canvas.nsview, 'release')
            self.canvas.nsview = None
            self.canvas = None

        # Do this last, so that we don't see white flash 
        # when exiting application from fullscreen mode.
        super(CocoaWindow, self).close()

        self._was_closed = True
        send_message(pool, 'drain')

    def switch_to(self):
        if self.context:
            self.context.set_current()

    def flip(self):
        self.draw_mouse_cursor()
        if self.context:
            self.context.flip()

    def dispatch_events(self):
        self._allow_dispatch_event = True
        # Process all pyglet events.
        self.dispatch_pending_events()
        event = True

        # Dequeue and process all of the pending Cocoa events.
        pool = alloc_init('NSAutoreleasePool')
        NSApp = send_message('NSApplication', 'sharedApplication')
        while event and self._nswindow and self._context:
            event = send_message(NSApp, 'nextEventMatchingMask:untilDate:inMode:dequeue:',
                                 NSAnyEventMask, None, NSEventTrackingRunLoopMode, True)

            if event.value is not None:
                event_type = send_message(event, 'type', restype=c_uint)
                # Pass on all events.
                send_message(NSApp, 'sendEvent:', event)
                # And resend key events to special handlers.
                if event_type == NSKeyDown and not send_message(event, 'isARepeat', restype=c_bool):
                    send_message(NSApp, 'sendAction:to:from:', get_selector('pygletKeyDown:'), None, event)
                elif event_type == NSKeyUp:
                    send_message(NSApp, 'sendAction:to:from:', get_selector('pygletKeyUp:'), None, event)
                elif event_type == NSFlagsChanged:
                    send_message(NSApp, 'sendAction:to:from:', get_selector('pygletFlagsChanged:'), None, event)
                send_message(NSApp, 'updateWindows')

        send_message(pool, 'drain')

        self._allow_dispatch_event = False

    def dispatch_pending_events(self):
        while self._event_queue:
            event = self._event_queue.pop(0)
            EventDispatcher.dispatch_event(self, *event)

    def set_caption(self, caption):
        self._caption = caption
        if self._nswindow is not None:
            send_message(self._nswindow, 'setTitle:', NSString(caption))

    def set_icon(self, *images):
        # Only use the biggest image from the list.
        max_image = images[0]
        for img in images:
            if img.width > max_image.width and img.height > max_image.height:
                max_image = img

        # Grab image data from pyglet image.
        image = max_image.get_image_data()
        format = 'ARGB'
        bytesPerRow = len(format) * image.width
        data = image.get_data(format, -bytesPerRow)

        # Use image data to create a data provider.
        # Using CGDataProviderCreateWithData crashes PyObjC 2.2b3, so we create
        # a CFDataRef object first and use it to create the data provider.
        cfdata = c_void_p(cf.CFDataCreate(None, data, len(data)))
        provider = c_void_p(quartz.CGDataProviderCreateWithCFData(cfdata))
        
        colorSpace = c_void_p(quartz.CGColorSpaceCreateDeviceRGB())

        # Then create a CGImage from the provider.
        cgimage = c_void_p(quartz.CGImageCreate(
            image.width, image.height, 8, 32, bytesPerRow,
            colorSpace,
            kCGImageAlphaFirst,
            provider,
            None,
            True,
            kCGRenderingIntentDefault))
        
        if not cgimage:
            return

        cf.CFRelease(cfdata)
        quartz.CGDataProviderRelease(provider)
        quartz.CGColorSpaceRelease(colorSpace)

        # Turn the CGImage into an NSImage.
        size = NSMakeSize(image.width, image.height)
        nsimage = send_message('NSImage', 'alloc')
        nsimage = send_message(nsimage, 'initWithCGImage:size:', cgimage, size, argtypes=[c_void_p, NSSize])
        if not nsimage:
            return

        # And finally set the app icon.
        NSApp = send_message('NSApplication', 'sharedApplication')
        send_message(NSApp, 'setApplicationIconImage:', nsimage)
        send_message(nsimage, 'release')

    def get_location(self):
        window_frame = send_message(self._nswindow, 'frame', restype=NSRect)        
        rect = send_message(self._nswindow, 'contentRectForFrameRect:', window_frame, restype=NSRect, argtypes=[NSRect])
        screen_frame = send_message(send_message(self._nswindow, 'screen'), 'frame', restype=NSRect)
        screen_width = int(screen_frame.size.width)
        screen_height = int(screen_frame.size.height)
        return int(rect.origin.x), int(screen_height - rect.origin.y - rect.size.height)

    def set_location(self, x, y):
        window_frame = send_message(self._nswindow, 'frame', restype=NSRect)        
        rect = send_message(self._nswindow, 'contentRectForFrameRect:', window_frame, restype=NSRect, argtypes=[NSRect])
        screen_frame = send_message(send_message(self._nswindow, 'screen'), 'frame', restype=NSRect)
        screen_width = int(screen_frame.size.width)
        screen_height = int(screen_frame.size.height)
        origin = NSPoint(x, screen_height - y - rect.size.height)
        send_message(self._nswindow, 'setFrameOrigin:', origin, argtypes=[NSPoint])

    def get_size(self):
        window_frame = send_message(self._nswindow, 'frame', restype=NSRect)        
        rect = send_message(self._nswindow, 'contentRectForFrameRect:', window_frame, restype=NSRect, argtypes=[NSRect])
        return int(rect.size.width), int(rect.size.height)

    def set_size(self, width, height):
        if self._fullscreen:
            raise WindowException('Cannot set size of fullscreen window.')
        self._width = max(1, int(width))
        self._height = max(1, int(height))
        # Move frame origin down so that top-left corner of window doesn't move.
        window_frame = send_message(self._nswindow, 'frame', restype=NSRect)        
        rect = send_message(self._nswindow, 'contentRectForFrameRect:', window_frame, restype=NSRect, argtypes=[NSRect])
        rect.origin.y += rect.size.height - self._height
        rect.size.width = self._width
        rect.size.height = self._height
        new_frame = send_message(self._nswindow, 'frameRectForContentRect:', rect, restype=NSRect, argtypes=[NSRect])
        # The window background flashes when the frame size changes unless it's
        # animated, but we can set the window's animationResizeTime to zero.
        is_visible = send_message(self._nswindow, 'isVisible', restype=c_bool)
        send_message(self._nswindow, 'setFrame:display:animate:', new_frame, True, is_visible,
                     argtypes=[NSRect, c_bool, c_bool])

    def set_minimum_size(self, width, height):
        self._minimum_size = NSSize(width, height)
        if self._nswindow is not None:
            send_message(self._nswindow, 'setContentMinSize:', self._minimum_size, argtypes=[NSSize])

    def set_maximum_size(self, width, height):
        self._maximum_size = NSSize(width, height)
        if self._nswindow is not None:
            send_message(self._nswindow, 'setContentMaxSize:', self._maximum_size, argtypes=[NSSize])

    def activate(self):
        if self._nswindow is not None:
            NSApp = send_message('NSApplication', 'sharedApplication')
            send_message(NSApp, 'activateIgnoringOtherApps:', True, argtypes=[c_bool])
            send_message(self._nswindow, 'makeKeyAndOrderFront:', None)

    def set_visible(self, visible=True):
        self._visible = visible
        if self._nswindow is not None:
            if visible:
                # Not really sure why on_resize needs to be here, 
                # but it's what pyglet wants.
                self.dispatch_event('on_resize', self._width, self._height)
                self.dispatch_event('on_show')
                self.dispatch_event('on_expose')
                send_message(self._nswindow, 'makeKeyAndOrderFront:', None)
            else:
                send_message(self._nswindow, 'orderOut:', None)

    def minimize(self):
        self._mouse_in_window = False
        if self._nswindow is not None:
            send_message(self._nswindow, 'miniaturize:', None)

    def maximize(self):
        if self._nswindow is not None:
            send_message(self._nswindow, 'zoom:', None)

    def set_vsync(self, vsync):
        if pyglet.options['vsync'] is not None:
            vsync = pyglet.options['vsync']
        self._vsync = vsync # _recreate depends on this
        if self.context:
            self.context.set_vsync(vsync)

    def _mouse_in_content_rect(self):
        # Returns true if mouse is inside the window's content rectangle.
        # Better to use this method to check manually rather than relying
        # on instance variables that may not be set correctly.
        point = send_message('NSEvent', 'mouseLocation', restype=NSPoint)
        window_frame = send_message(self._nswindow, 'frame', restype=NSRect)        
        rect = send_message(self._nswindow, 'contentRectForFrameRect:', window_frame, restype=NSRect, argtypes=[NSRect])
        return foundation.NSMouseInRect(point, rect, False)

    def set_mouse_platform_visible(self, platform_visible=None):
        # When the platform_visible argument is supplied with a boolean, then this
        # method simply sets whether or not the platform mouse cursor is visible.
        if platform_visible is not None:
            if platform_visible:
                SystemCursor.unhide()
            else:
                SystemCursor.hide()
        # But if it has been called without an argument, it turns into
        # a completely different function.  Now we are trying to figure out
        # whether or not the mouse *should* be visible, and if so, what it should
        # look like.
        else:
            # If we are in mouse exclusive mode, then hide the mouse cursor.
            if self._is_mouse_exclusive:
                SystemCursor.hide()
            # If we aren't inside the window, then always show the mouse
            # and make sure that it is the default cursor.
            elif not self._mouse_in_content_rect():
                send_message(send_message('NSCursor', 'arrowCursor'), 'set')
                SystemCursor.unhide()
            # If we are in the window, then what we do depends on both
            # the current pyglet-set visibility setting for the mouse and
            # the type of the mouse cursor.  If the cursor has been hidden
            # in the window with set_mouse_visible() then don't show it.
            elif not self._mouse_visible:
                SystemCursor.hide()
            # If the mouse is set as a system-defined cursor, then we
            # need to set the cursor and show the mouse.
            # *** FIX ME ***
            elif isinstance(self._mouse_cursor, CocoaMouseCursor):
                self._mouse_cursor.set()
                SystemCursor.unhide()
            # If the mouse cursor is drawable, then it we need to hide
            # the system mouse cursor, so that the cursor can draw itself.
            elif self._mouse_cursor.drawable:
                SystemCursor.hide()
            # Otherwise, show the default cursor.
            else:
                send_message(send_message('NSCursor', 'arrowCursor'), 'set')
                SystemCursor.unhide()

    def get_system_mouse_cursor(self, name):
        # It would make a lot more sense for most of this code to be
        # inside the CocoaMouseCursor class, but all of the CURSOR_xxx
        # constants are defined as properties of BaseWindow.
        if name == self.CURSOR_DEFAULT:
            return DefaultMouseCursor()
        cursors = {
            self.CURSOR_CROSSHAIR:       'crosshairCursor',
            self.CURSOR_HAND:            'pointingHandCursor',
            self.CURSOR_HELP:            'arrowCursor',
            self.CURSOR_NO:              'operationNotAllowedCursor', # Mac OS 10.6
            self.CURSOR_SIZE:            'arrowCursor',
            self.CURSOR_SIZE_UP:         'resizeUpCursor',
            self.CURSOR_SIZE_UP_RIGHT:   'arrowCursor',
            self.CURSOR_SIZE_RIGHT:      'resizeRightCursor',
            self.CURSOR_SIZE_DOWN_RIGHT: 'arrowCursor',
            self.CURSOR_SIZE_DOWN:       'resizeDownCursor',
            self.CURSOR_SIZE_DOWN_LEFT:  'arrowCursor',
            self.CURSOR_SIZE_LEFT:       'resizeLeftCursor',
            self.CURSOR_SIZE_UP_LEFT:    'arrowCursor',
            self.CURSOR_SIZE_UP_DOWN:    'resizeUpDownCursor',
            self.CURSOR_SIZE_LEFT_RIGHT: 'resizeLeftRightCursor',
            self.CURSOR_TEXT:            'IBeamCursor',
            self.CURSOR_WAIT:            'arrowCursor', # No wristwatch cursor in Cocoa
            self.CURSOR_WAIT_ARROW:      'arrowCursor', # No wristwatch cursor in Cocoa
            }  
        if name not in cursors:
            raise RuntimeError('Unknown cursor name "%s"' % name)
        return CocoaMouseCursor(cursors[name])

    def set_mouse_position(self, x, y, absolute=False):
        if absolute:
            # If absolute, then x, y is given in global display coordinates
            # which sets (0,0) at top left corner of main display.  It is possible
            # to warp the mouse position to a point inside of another display.
            quartz.CGWarpMouseCursorPosition(CGPoint(x,y))
        else: 
            # Window-relative coordinates: (x, y) are given in window coords
            # with (0,0) at bottom-left corner of window and y up.  We find
            # which display the window is in and then convert x, y into local
            # display coords where (0,0) is now top-left of display and y down.
            screenInfo = send_message(send_message(self._nswindow, 'screen'), 'deviceDescription')
            displayID = send_message(screenInfo, 'objectForKey:', NSString('NSScreenNumber'))
            displayID = send_message(displayID, 'intValue', restype=c_int) # is this right?
            displayBounds = quartz.CGDisplayBounds(displayID)
            frame = send_message(self._nswindow, 'frame', restype=NSRect)        
            windowOrigin = frame.origin
            x += windowOrigin.x
            y = displayBounds.size.height - windowOrigin.y - y
            quartz.CGDisplayMoveCursorToPoint(displayID, NSPoint(x,y))

    def set_exclusive_mouse(self, exclusive=True):
        self._is_mouse_exclusive = exclusive
        if exclusive:
            # Skip the next motion event, which would return a large delta.
            self._mouse_ignore_motion = True
            # Move mouse to center of window.
            frame = send_message(self._nswindow, 'frame', restype=NSRect)        
            width, height = frame.size.width, frame.size.height
            self.set_mouse_position(width/2, height/2)
            quartz.CGAssociateMouseAndMouseCursorPosition(False)
        else:
            quartz.CGAssociateMouseAndMouseCursorPosition(True)

        # Update visibility of mouse cursor.
        self.set_mouse_platform_visible()

    def set_exclusive_keyboard(self, exclusive=True):
        # http://developer.apple.com/mac/library/technotes/tn2002/tn2062.html
        # http://developer.apple.com/library/mac/#technotes/KioskMode/

        # BUG: System keys like F9 or command-tab are disabled, however 
        # pyglet also does not receive key press events for them.

        # This flag is queried by window delegate to determine whether 
        # the quit menu item is active.
        self._is_keyboard_exclusive = exclusive
            
        if exclusive:
            # "Be nice! Don't disable force-quit!" 
            #          -- Patrick Swayze, Road House (1989)
            options = NSApplicationPresentationHideDock | \
                      NSApplicationPresentationHideMenuBar | \
                      NSApplicationPresentationDisableProcessSwitching | \
                      NSApplicationPresentationDisableHideApplication
        else:
            options = NSApplicationPresentationDefault

        NSApp = send_message('NSApplication', 'sharedApplication')
        send_message(NSApp, 'setPresentationOptions:', options, argtypes=[NSUInteger])
