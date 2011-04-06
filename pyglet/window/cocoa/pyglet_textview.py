import unicodedata

from pyglet.window import key

from pyglet.libs.darwin.objc_runtime import *


# This custom NSTextView subclass is used for capturing all of the
# on_text, on_text_motion, and on_text_motion_select events.
class PygletTextView_Implementation(object):
    PygletTextView = ObjCSubclass('NSTextView', 'PygletTextView')

    @PygletTextView.initmethod('@@')
    def initWithCocoaWindow_(self, window):
        window = cast_to_pyobject(window)
        self.objc_self = send_super(self, 'init')
        if self.objc_self is not None:
            self._window = window
            # Interpret tab and return as raw characters
            send_message(self.objc_self, 'setFieldEditor:', False, argtypes=[c_bool])
        self.empty_string = CFSTR("")
        return self

    @PygletTextView.dealloc
    def dealloc(self):
        send_message(self.empty_string, 'release')

    @PygletTextView.method('v@')
    def keyDown_(self, nsevent):
        array = send_message('NSArray', 'arrayWithObject:', c_void_p(nsevent), argtypes=[c_void_p])
        send_message(self.objc_self, 'interpretKeyEvents:', array, argtypes=[c_void_p])

    @PygletTextView.method('v@')
    def insertText_(self, text):
        text = cfstring_to_string(text)
        send_message(self.objc_self, 'setString:', self.empty_string)
        # Don't send control characters (tab, newline) as on_text events.
        if unicodedata.category(text[0]) != 'Cc':
            self._window.dispatch_event("on_text", text)

    @PygletTextView.method('v@')
    def insertNewline_(self, sender):
        # Distinguish between carriage return (u'\r') and enter (u'\x03').
        # Only the return key press gets sent as an on_text event.
        event = send_message(send_message('NSApplication', 'sharedApplication'), 'currentEvent')
        chars = send_message(event, 'charactersIgnoringModifiers')
        ch = send_message(chars, 'characterAtIndex:', 0, restype=unichar, argtypes=[NSUInteger])
        if ch == u'\r':
            self._window.dispatch_event("on_text", u'\r')

    @PygletTextView.method('v@')
    def moveUp_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_UP)

    @PygletTextView.method('v@')
    def moveDown_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_DOWN)

    @PygletTextView.method('v@')
    def moveLeft_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_LEFT)

    @PygletTextView.method('v@')
    def moveRight_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_RIGHT)

    @PygletTextView.method('v@')
    def moveWordLeft_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_PREVIOUS_WORD)        

    @PygletTextView.method('v@')
    def moveWordRight_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_NEXT_WORD)        

    @PygletTextView.method('v@')
    def moveToBeginningOfLine_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_BEGINNING_OF_LINE)

    @PygletTextView.method('v@')
    def moveToEndOfLine_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_END_OF_LINE)

    @PygletTextView.method('v@')
    def scrollPageUp_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_PREVIOUS_PAGE)

    @PygletTextView.method('v@')
    def scrollPageDown_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_NEXT_PAGE)

    @PygletTextView.method('v@')
    def scrollToBeginningOfDocument_(self, sender):   # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion", key.MOTION_BEGINNING_OF_FILE)

    @PygletTextView.method('v@')
    def scrollToEndOfDocument_(self, sender):         # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion", key.MOTION_END_OF_FILE)

    @PygletTextView.method('v@')
    def deleteBackward_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_BACKSPACE)

    @PygletTextView.method('v@')
    def deleteForward_(self, sender):
        self._window.dispatch_event("on_text_motion", key.MOTION_DELETE)

    @PygletTextView.method('v@')
    def moveUpAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_UP)

    @PygletTextView.method('v@')
    def moveDownAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_DOWN)

    @PygletTextView.method('v@')
    def moveLeftAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_LEFT)

    @PygletTextView.method('v@')
    def moveRightAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_RIGHT)

    @PygletTextView.method('v@')
    def moveWordLeftAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_PREVIOUS_WORD)        

    @PygletTextView.method('v@')
    def moveWordRightAndModifySelection_(self, sender):
        self._window.dispatch_event("on_text_motion_select", key.MOTION_NEXT_WORD)        

    @PygletTextView.method('v@')
    def moveToBeginningOfLineAndModifySelection_(self, sender):      # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_BEGINNING_OF_LINE)

    @PygletTextView.method('v@')
    def moveToEndOfLineAndModifySelection_(self, sender):            # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_END_OF_LINE)

    @PygletTextView.method('v@')
    def pageUpAndModifySelection_(self, sender):                     # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_PREVIOUS_PAGE)

    @PygletTextView.method('v@')
    def pageDownAndModifySelection_(self, sender):                   # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_NEXT_PAGE)

    @PygletTextView.method('v@')
    def moveToBeginningOfDocumentAndModifySelection_(self, sender):  # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_BEGINNING_OF_FILE)

    @PygletTextView.method('v@')
    def moveToEndOfDocumentAndModifySelection_(self, sender):        # Mac OS X 10.6
        self._window.dispatch_event("on_text_motion_select", key.MOTION_END_OF_FILE)
