from pyglet.libs.darwin.objc_runtime import *

class PygletWindow_Implementation(object):
    PygletWindow = ObjCSubclass('NSWindow', 'PygletWindow')

    @PygletWindow.dealloc
    def dealloc(self):
        send_super(self, 'dealloc')        

    @PygletWindow.method('B')
    def canBecomeKeyWindow(self):
        return True

    # When the window is being resized, it enters into a mini event loop that
    # only looks at mouseDragged and mouseUp events, blocking everything else.
    # Among other things, this makes it impossible to run an NSTimer to call the
    # idle() function in order to update the view during the resize.  So we
    # override this method, called by the resizing event loop, and call the
    # idle() function from here.  This *almost* works.  I can't figure out what
    # is happening at the very beginning of a resize event.  The NSView's
    # viewWillStartLiveResize method is called and then nothing happens until
    # the mouse is dragged.  I think NSApplication's nextEventMatchingMask_etc
    # method is being called instead of this one.  I don't really feel like
    # subclassing NSApplication just to fix this.  Also, to prevent white flashes
    # while resizing, we must also call idle() from the view's reshape method.
    @PygletWindow.method('@'+NSUIntegerEncoding+'@@c')
    def nextEventMatchingMask_untilDate_inMode_dequeue_(self, mask, date, mode, dequeue):
        if send_message(self.objc_self, 'inLiveResize', restype=c_bool):
            # Call the idle() method while we're stuck in a live resize event.
            from pyglet import app
            if app.event_loop is not None:
                app.event_loop.idle()
         
        send_super(self.objc_self, 'nextEventMatchingMask:untilDate:inMode:dequeue:', 
                   mask, date, mode, dequeue, argtypes=[NSUInteger, c_void_p, c_void_p, c_bool])

    # Need this for set_size to not flash.
    @PygletWindow.method('d'+NSRectEncoding)
    def animationResizeTime_(self, newFrame):
        return 0.0


class PygletToolWindow_Implementation(object):
    PygletToolWindow = ObjCSubclass('NSPanel', 'PygletToolWindow')

    @PygletToolWindow.dealloc
    def dealloc(self):
        send_super(self, 'dealloc')        

    @PygletToolWindow.method('@'+NSUIntegerEncoding+'@@c')
    def nextEventMatchingMask_untilDate_inMode_dequeue_(self, mask, date, mode, dequeue):
        if send_message(self.objc_self, 'inLiveResize', restype=c_bool):
            # Call the idle() method while we're stuck in a live resize event.
            from pyglet import app
            if app.event_loop is not None:
                app.event_loop.idle()
                
        send_super(self.objc_self, 'nextEventMatchingMask:untilDate:inMode:dequeue:', 
                   mask, date, mode, dequeue, argtypes=[NSUInteger, c_void_p, c_void_p, c_bool])

    # Need this for set_size to not flash.
    @PygletToolWindow.method('d'+NSRectEncoding)
    def animationResizeTime_(self, newFrame):
        return 0.0
