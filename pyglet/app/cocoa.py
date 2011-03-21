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

from pyglet.app.base import PlatformEventLoop
from pyglet.libs.darwin.objc_runtime import *

def add_menu_item(menu, title, action, key):
    menuItem = send_message('NSMenuItem', 'alloc')
    title = CFSTR(title)
    action = get_selector(action)
    key = CFSTR(key)
    send_message(menuItem, 'initWithTitle:action:keyEquivalent:', title, action, key)
    send_message(menu, 'addItem:', menuItem)
    # cleanup
    send_message(title, 'release')
    send_message(key, 'release')
    send_message(menuItem, 'release')

def create_menu():
    nsapp = send_message('NSApplication', 'sharedApplication')
    menubar = alloc_init_autorelease('NSMenu')
    appMenuItem = alloc_init_autorelease('NSMenuItem')
    send_message(menubar, 'addItem:', appMenuItem)
    send_message(nsapp, 'setMainMenu:', menubar)
    appMenu = alloc_init_autorelease('NSMenu')

    # Hide still doesn't work!?
    add_menu_item(appMenu, 'Hide!', 'hide:', 'h')
    send_message(appMenu, 'addItem:', send_message('NSMenuItem', 'separatorItem'))
    add_menu_item(appMenu, 'Quit!', 'terminate:', 'q')

    send_message(appMenuItem, 'setSubmenu:', appMenu)

class CocoaEventLoop(PlatformEventLoop):

    def __init__(self):
        super(CocoaEventLoop, self).__init__()
        # Prepare the default application.
        self.NSApp = send_message('NSApplication', 'sharedApplication')
        # Create an autorelease pool for menu creation and finishLaunching
        self.pool = alloc_init('NSAutoreleasePool')
        create_menu()
        send_message(self.NSApp, 'finishLaunching')
        send_message(self.NSApp, 'activateIgnoringOtherApps:', True)
        #send_message(self.pool, 'drain')

    def start(self):
        pass

    def step(self, timeout=None):
        # Create an autorelease pool for this iteration.
        send_message(self.pool, 'drain')
        self.pool = alloc_init('NSAutoreleasePool')

        # Determine the timeout date.
        if timeout is None:
            # Using distantFuture as untilDate means that nextEventMatchingMask
            # will wait until the next event comes along.
            timeout_date = send_message('NSDate', 'distantFuture')
        else:
            timeout_date = send_message('NSDate', 'dateWithTimeIntervalSinceNow:', timeout, argtypes=[c_double])

        # Retrieve the next event (if any).  We wait for an event to show up
        # and then process it, or if timeout_date expires we simply return.
        # We only process one event per call of step().
        self._is_running.set()
        event = send_message(self.NSApp, 'nextEventMatchingMask:untilDate:inMode:dequeue:',
                NSAnyEventMask, timeout_date, NSDefaultRunLoopMode, True)

        # Dispatch the event (if any).
        if event is not None:
            event_type = send_message(event, 'type', restype=c_uint)
            if event_type != NSApplicationDefined:
                # Send out event as normal.  Responders will still receive 
                # keyUp:, keyDown:, and flagsChanged: events.
                send_message(self.NSApp, 'sendEvent:', event)

                # Resend key events as special pyglet-specific messages
                # which supplant the keyDown:, keyUp:, and flagsChanged: messages
                # because NSApplication translates multiple key presses into key 
                # equivalents before sending them on, which means that some keyUp:
                # messages are never sent for individual keys.   Our pyglet-specific
                # replacements ensure that we see all the raw key presses & releases.
                # We also filter out key-down repeats since pyglet only sends one
                # on_key_press event per key press.
                if event_type == NSKeyDown and not send_message(event, 'isARepeat', restype=c_bool):
                    send_message(self.NSApp, 'sendAction:to:from:', get_selector('pygletKeyDown:'), None, event)
                elif event_type == NSKeyUp:
                    send_message(self.NSApp, 'sendAction:to:from:', get_selector('pygletKeyUp:'), None, event)
                elif event_type == NSFlagsChanged:
                    send_message(self.NSApp, 'sendAction:to:from:', get_selector('pygletFlagsChanged:'), None, event)

            send_message(self.NSApp, 'updateWindows')
            did_time_out = False
        else:
            did_time_out = True

        self._is_running.clear()

        # Destroy the autorelease pool used for this step.
        #send_message(pool, 'drain')
        
        return did_time_out
    
    def stop(self):
        pass

    def notify(self):
        pool = alloc_init('NSAutoreleasePool')
        notifyEvent = send_message('NSEvent', 'otherEventWithType:location:modifierFlags:timestamp:windowNumber:context:subtype:data1:data2:',
                                   NSApplicationDefined, # type
                                   NSPoint(0.0, 0.0),    # location
                                   0,                    # modifierFlags
                                   0,                    # timestamp
                                   0,                    # windowNumber
                                   None,                 # graphicsContext
                                   0,                    # subtype
                                   0,                    # data1
                                   0,                    # data2
                                   argtypes=[NSUInteger, NSPoint, NSUInteger, NSTimeInterval, NSInteger, c_void_p, c_short, NSInteger, NSInteger])
        send_message(self.NSApp, 'postEvent:atStart:', notifyEvent, False, argtypes=[c_void_p, c_bool])
        send_message(pool, 'drain')
