from ctypes import *
from ctypes import util

import sys
__LP64__ = (sys.maxint > 2**32)


######################################################################

objc = cdll.LoadLibrary(util.find_library('objc'))

objc.sel_registerName.restype = c_void_p
objc.sel_registerName.argtypes = [c_char_p]

objc.objc_msgSend.restype = c_void_p

objc.objc_getClass.restype = c_void_p
objc.objc_getClass.argtypes = [c_char_p]

objc.objc_getMetaClass.restype = c_void_p
objc.objc_getMetaClass.argtypes = [c_char_p]

objc.objc_allocateClassPair.restype = c_void_p
objc.objc_allocateClassPair.argtypes = [c_void_p, c_char_p, c_size_t]

objc.objc_registerClassPair.restype = None
objc.objc_registerClassPair.argtypes = [c_void_p]

objc.class_addMethod.restype = None

objc.class_getSuperclass.restype = c_void_p
objc.class_getSuperclass.argtypes = [c_void_p]

objc.class_addIvar.restype = c_bool
objc.class_addIvar.argtypes = [c_void_p, c_char_p, c_size_t, c_uint8, c_char_p]

objc.class_getInstanceMethod.restype = c_void_p
objc.class_getInstanceMethod.argtypes = [c_void_p, c_void_p]

objc.object_getClass.restype = c_void_p
objc.object_getClass.argtypes = [c_void_p]

objc.object_setInstanceVariable.restype = c_void_p

objc.object_getInstanceVariable.restype = c_void_p
objc.object_getInstanceVariable.argtypes=[c_void_p, c_char_p, c_void_p]

objc.method_getTypeEncoding.restype = c_char_p
objc.method_getTypeEncoding.argtypes = [c_void_p]

def get_selector(name):
    return c_void_p(objc.sel_registerName(name))

def get_class(name):
    return c_void_p(objc.objc_getClass(name))

def get_metaclass(name):
    return c_void_p(objc.objc_getMetaClass(name))

def get_superclass_of_object(obj):
    cls = c_void_p(objc.object_getClass(obj))
    return c_void_p(objc.class_getSuperclass(cls))


# http://www.sealiesoftware.com/blog/archive/2008/10/30/objc_explain_objc_msgSend_stret.html
# http://www.x86-64.org/documentation/abi-0.99.pdf  (pp.17-23)
# executive summary: on x86-64, who knows?
def x86_should_use_stret(restype):
    """Try to figure out when a return type will be passed on stack."""
    if type(restype) != type(Structure):
        return False
    if not __LP64__ and sizeof(restype) <= 8:
        return False
    if __LP64__ and sizeof(restype) <= 16:  # maybe? I don't know?
        return False
    return True

# By default, assumes that restype is c_void_p
# and that all arguments are wrapped inside c_void_p.
# Use the restype and argtypes keyword arguments to 
# change these values.  restype should be a ctypes type
# and argtypes should be a list of ctypes types for
# the arguments of the message only.
def send_message(receiver, selName, *args, **kwargs):
    if isinstance(receiver, basestring):
        receiver = get_class(receiver)
    selector = get_selector(selName)
    restype = kwargs.get('restype', c_void_p)
    #print 'send_message', receiver, selName, args, kwargs
    argtypes = kwargs.get('argtypes', [])
    # Choose the correct version of objc_msgSend based on return type.
    if restype in (c_float, c_double, c_longdouble):  # not valid on PPC
        objc.objc_msgSend_fpret.restype = restype
        objc.objc_msgSend_fpret.argtypes = [c_void_p, c_void_p] + argtypes
        result = objc.objc_msgSend_fpret(receiver, selector, *args)
    elif x86_should_use_stret(restype):
        objc.objc_msgSend_stret.restype = None
        objc.objc_msgSend_stret.argtypes = [POINTER(restype), c_void_p, c_void_p] + argtypes
        result = restype()
        objc.objc_msgSend_stret(byref(result), receiver, selector, *args)
    else:
        objc.objc_msgSend.restype = restype
        objc.objc_msgSend.argtypes = [c_void_p, c_void_p] + argtypes
        result = objc.objc_msgSend(receiver, selector, *args)
        if restype == c_void_p:
            result = c_void_p(result)
    return result

class OBJC_SUPER(Structure):
    _fields_ = [ ('receiver', c_void_p), ('class', c_void_p) ]

OBJC_SUPER_PTR = POINTER(OBJC_SUPER)

#http://stackoverflow.com/questions/3095360/what-exactly-is-super-in-objective-c
def send_super(receiver, selName, *args, **kwargs):
    #print 'send_super', receiver, selName, args
    if hasattr(receiver, '_as_parameter_'):
        receiver = receiver._as_parameter_
    superclass = get_superclass_of_object(receiver)
    super_struct = OBJC_SUPER(receiver, superclass)
    selector = get_selector(selName)
    restype = kwargs.get('restype', c_void_p)
    argtypes = kwargs.get('argtypes', None)
    objc.objc_msgSendSuper.restype = restype
    if argtypes:
        objc.objc_msgSendSuper.argtypes = [OBJC_SUPER_PTR, c_void_p] + argtypes
    else:
        objc.objc_msgSendSuper.argtypes = None
    result = objc.objc_msgSendSuper(byref(super_struct), selector, *args)
    if restype == c_void_p:
        result = c_void_p(result)
    return result

# After calling create_subclass, you must first register
# it with register_subclass before you may use it.
# You can add new methods after the class is registered,
# but you cannot add any new ivars.
def create_subclass(superclass, name):
    if isinstance(superclass, basestring):
        superclass = get_class(superclass)
    return c_void_p(objc.objc_allocateClassPair(superclass, name, 0))

def register_subclass(subclass):
    objc.objc_registerClassPair(subclass)

# Convenience functions for creating new objects.
def alloc_init(cls):
    return send_message(cls, 'new')

def alloc_init_autorelease(cls):
    return send_message(send_message(cls, 'new'), 'autorelease')

######################################################################

def encoding_for_ctype(vartype):
    typecodes = {c_char:'c', c_int:'i', c_short:'s', c_long:'l', c_longlong:'q',
                 c_ubyte:'C', c_uint:'I', c_ushort:'S', c_ulong:'L', c_ulonglong:'Q',
                 c_float:'f', c_double:'d', c_bool:'B', c_char_p:'*', c_void_p:'@',
                 py_object:'@'}
    return typecodes.get(vartype, '?')

# Note CGBase.h located at
# /System/Library/Frameworks/ApplicationServices.framework/Frameworks/CoreGraphics.framework/Headers/CGBase.h
# defines CGFloat as double if __LP64__, otherwise it's a float.
if __LP64__:
    NSInteger = c_long
    NSUInteger = c_ulong
    CGFloat = c_double
    NSPointEncoding = '{CGPoint=dd}'
    NSSizeEncoding = '{CGSize=dd}'
    NSRectEncoding = '{CGRect={CGPoint=dd}{CGSize=dd}}'
else:
    NSInteger = c_int
    NSUInteger = c_uint
    CGFloat = c_float
    NSPointEncoding = '{NSPoint=ff}'
    NSSizeEncoding = '{NSSize=ff}'
    NSRectEncoding = '{NSRect={NSPoint=ff}{NSSize=ff}}'

NSIntegerEncoding = encoding_for_ctype(NSInteger)
NSUIntegerEncoding = encoding_for_ctype(NSUInteger)
CGFloatEncoding = encoding_for_ctype(CGFloat)    

# from /System/Library/Frameworks/Foundation.framework/Headers/NSGeometry.h
class NSPoint(Structure):
    _fields_ = [ ("x", CGFloat), ("y", CGFloat) ]
CGPoint = NSPoint

class NSSize(Structure):
    _fields_ = [ ("width", CGFloat), ("height", CGFloat) ]

class NSRect(Structure):
    _fields_ = [ ("origin", NSPoint), ("size", NSSize) ]
CGRect = NSRect

def NSMakeSize(w, h):
    return NSSize(w, h)

def NSMakeRect(x, y, w, h):
    return NSRect(NSPoint(x, y), NSSize(w, h))

# NSDate.h
NSTimeInterval = c_double

CFIndex = c_long
UniChar = c_ushort
unichar = c_wchar  # (actually defined as c_ushort in NSString.h, but need ctypes to convert properly)
CGGlyph = c_ushort

# CFRange struct defined in CFBase.h
# This replaces the CFRangeMake(LOC, LEN) macro.
class CFRange(Structure):
    _fields_ = [ ("location", CFIndex), ("length", CFIndex) ]

# NSRange.h  (Note, not defined the same as CFRange)
class NSRange(Structure):
    _fields_ = [ ("location", NSUInteger), ("length", NSUInteger) ]

NSZeroPoint = NSPoint(0,0)

######################################################################

cfunctype_table = {}

def tokenize_encoding(encoding):
    token_list = []
    brace_count = 0
    token = ''
    for c in encoding:
        token += c
        if c == '{':
            brace_count += 1
        elif c == '}':
            brace_count -= 1
            if brace_count < 0: # bad encoding
                brace_count = 0
        if brace_count == 0:
            token_list.append(token)
            token = ''
    return token_list

# Limited to basic types and pointers to basic types.
# Does not try to handle arrays, structs, unions, or bitfields.
def cfunctype_for_encoding(encoding):
    # Check if we've already created a CFUNCTYPE for this encoding.
    # If so, then return the cached CFUNCTYPE.
    if encoding in cfunctype_table:
        return cfunctype_table[encoding]

    # Otherwise, create a new CFUNCTYPE for the encoding.
    typecodes = {'c':c_char, 'i':c_int, 's':c_short, 'l':c_long, 'q':c_longlong, 
                 'C':c_ubyte, 'I':c_uint, 'S':c_ushort, 'L':c_ulong, 'Q':c_ulonglong, 
                 'f':c_float, 'd':c_double, 'B':c_bool, 'v':None, '*':c_char_p,
                 '@':c_void_p, '#':c_void_p, ':':c_void_p, NSPointEncoding:NSPoint,
                 NSSizeEncoding:NSSize, NSRectEncoding:NSRect}
    argtypes = []
    pointer = False
    for token in tokenize_encoding(encoding):
        if pointer:
            if token in typecodes:
                argtypes.append(POINTER(typecodes[token]))
                pointer = False
            else:
                raise Exception('unknown encoding')
        else:
            if token in typecodes:
                argtypes.append(typecodes[token])
            elif token == '^':
                pointer = True
            else:
                raise Exception('unknown encoding: ' + token)
    cfunctype = CFUNCTYPE(*argtypes)
    # Cache the new CFUNCTYPE in the cfunctype_table.
    # We do this mainly because it prevents the CFUNCTYPE 
    # from being garbage-collected while we need it.
    cfunctype_table[encoding] = cfunctype
    return cfunctype

######################################################################

# types is a string encoding the argument types of the method.
# The first char of types is the return type ('v' if void)
# The second char must be '@' for id self.
# The third char must be ':' for SEL cmd.
# Additional chars are for types of other arguments if any.
def add_method(cls, selName, method, types):
    assert(types[1:3] == '@:')
    selector = get_selector(selName)
    cfunctype = cfunctype_for_encoding(types)
    imp = cfunctype(method)
    objc.class_addMethod.argtypes = [c_void_p, c_void_p, cfunctype, c_char_p]
    objc.class_addMethod(cls, selector, imp, types)
    return imp

def add_ivar(cls, name, vartype):
    return objc.class_addIvar(cls, name, sizeof(vartype), alignment(vartype), encoding_for_ctype(vartype))

def set_instance_variable(obj, varname, value, vartype):
    objc.object_setInstanceVariable.argtypes = [c_void_p, c_char_p, vartype]
    objc.object_setInstanceVariable(obj, varname, value)
    
def get_instance_variable(obj, varname, vartype):
    variable = vartype()
    objc.object_getInstanceVariable(obj, varname, byref(variable))
    return variable.value

def cast_to_pyobject(obj):
    return cast(obj, py_object).value

######################################################################

cf = cdll.LoadLibrary(util.find_library('CoreFoundation'))

kCFStringEncodingUTF8 = 0x08000100
CFAllocatorRef = c_void_p
CFStringEncoding = c_uint32

cf.CFStringCreateWithCString.restype = c_void_p
cf.CFStringCreateWithCString.argtypes = [CFAllocatorRef, c_char_p, CFStringEncoding]

cf.CFRelease.restype = c_void_p
cf.CFRelease.argtypes = [c_void_p]

cf.CFStringGetLength.restype = CFIndex
cf.CFStringGetLength.argtypes = [c_void_p]

cf.CFStringGetMaximumSizeForEncoding.restype = CFIndex
cf.CFStringGetMaximumSizeForEncoding.argtypes = [CFIndex, CFStringEncoding]

cf.CFStringGetCString.restype = c_bool
cf.CFStringGetCString.argtypes = [c_void_p, c_char_p, CFIndex, CFStringEncoding]

def CFSTR(string):
    return c_void_p(cf.CFStringCreateWithCString(
            None, string.encode('utf8'), kCFStringEncodingUTF8))

def NSString(string):
    """Autoreleased version of CFSTR"""
    return send_message(CFSTR(string), 'autorelease')

def cfstring_to_string(cfstring):
    length = cf.CFStringGetLength(cfstring)
    size = cf.CFStringGetMaximumSizeForEncoding(length, kCFStringEncodingUTF8)
    buffer = c_buffer(size + 1)
    result = cf.CFStringGetCString(cfstring, buffer, len(buffer), kCFStringEncodingUTF8)
    if result:
        return unicode(buffer.value, 'utf-8')

cf.CFArrayGetValueAtIndex.restype = c_void_p
cf.CFArrayGetValueAtIndex.argtypes = [c_void_p, CFIndex]

def cfarray_to_list(cfarray):
    count = cf.CFArrayGetCount(cfarray)
    return [ c_void_p(cf.CFArrayGetValueAtIndex(cfarray, i))
             for i in range(count) ]

cf.CFDataCreate.restype = c_void_p
cf.CFDataCreate.argtypes = [c_void_p, c_void_p, CFIndex]

cf.CFDictionaryGetValue.restype = c_void_p
cf.CFDictionaryGetValue.argtypes = [c_void_p, c_void_p]

# Helper function to convert CFNumber to a Python float.
kCFNumberFloatType = 12
def cfnumber_to_float(cfnumber):
    result = c_float()
    if cf.CFNumberGetValue(cfnumber, kCFNumberFloatType, byref(result)):
        return result.value

######################################################################

# This is a factory class which creates Objective-C subclasses.
# The python object created when you instantiate this class
# represents the Objective-C *class*.  It does not represent
# an instance of that class.  Instances are created by using 
# the normal Ojective-C alloc & init messages sent to the
# subclass with send_message.
class ObjCSubclass(object):

    def __init__(self, superclass, name):
        class PythonSelf(object):
            def __init__(self, objc_self):
                self.objc_self = objc_self
                # _as_parameter_ is used if this is passed as an argument
                # and argtypes not set.
                self._as_parameter_ = c_void_p(objc_self)
            def from_param(self):
                # Only called when PythonSelf is given as argtypes
                return c_void_p(self.objc_self)
        self.PythonSelf = PythonSelf

        self._object_table = {}
        self._imp_table = {}
        self.name = name
        self.objc_cls = create_subclass(superclass, name)
        self._as_parameter_ = self.objc_cls
        self.register()
        self.objc_metaclass = get_metaclass(name)

    def register(self):
        register_subclass(self.objc_cls)

    def add_ivar(self, varname, vartype):
        add_ivar(self.objc_cls, varname, vartype)

    def add_method(self, method, name, encoding):
        imp = add_method(self.objc_cls, name, method, encoding)
        self._imp_table[name] = imp

    # http://iphonedevelopment.blogspot.com/2008/08/dynamically-adding-class-objects.html
    def add_class_method(self, method, name, encoding):
        imp = add_method(self.objc_metaclass, name, method, encoding)
        self._imp_table[name] = imp
        
    def get_python_self_for_instance(self, objc_self):
        if isinstance(objc_self, c_void_p):
            objc_self = objc_self.value
        if objc_self in self._object_table:
            py_self = self._object_table[objc_self]
        else:
            py_self = self.PythonSelf(objc_self)
            self._object_table[objc_self] = py_self
        return py_self

    def delete_python_self(self, py_self):
        key = py_self.objc_self
        if hasattr(key, 'value'):
            key = key.value
        if key in self._object_table:
            del self._object_table[key]
        py_self.objc_self = None
        
    def method(self, encoding):
        """Function decorator for instance methods."""
        # Add encodings for hidden self and cmd arguments.
        encoding = encoding[0] + '@:' + encoding[1:]
        def decorator(f):
            def objc_method(objc_self, objc_cmd, *args):
                py_self = self.get_python_self_for_instance(objc_self)
                py_self.objc_cmd = objc_cmd
                result = f(py_self, *args)
                py_self.objc_self = objc_self   # restore in case accidentally changed
                return result
            name = f.func_name.replace('_', ':')
            self.add_method(objc_method, name, encoding)
            return objc_method
        return decorator

    def classmethod(self, encoding):
        """Function decorator for class methods."""
        # Add encodings for hidden self and cmd arguments.
        encoding = encoding[0] + '@:' + encoding[1:]
        def decorator(f):
            def objc_class_method(objc_cls, objc_cmd, *args):
                self.objc_cmd = objc_cmd
                return f(self, *args)
            name = f.func_name.replace('_', ':')
            self.add_class_method(objc_class_method, name, encoding)
            return objc_class_method
        return decorator

    def initmethod(self, encoding):
        """Function decorator for instance initializer method."""
        # Add encodings for hidden self and cmd arguments.
        encoding = encoding[0] + '@:' + encoding[1:]
        def decorator(f):
            def objc_init_method(objc_self, objc_cmd, *args):
                py_self = self.get_python_self_for_instance(objc_self)
                py_self.objc_cmd = objc_cmd
                result = f(py_self, *args)
                if isinstance(result, self.PythonSelf):
                    result = result.objc_self
                if isinstance(result, c_void_p):
                    result = result.value
                # Check if the value of objc_self was changed.
                if result != objc_self:
                    # Update entry in object_table.
                    del self._object_table[objc_self]
                    self._object_table[result] = py_self
                return result
            name = f.func_name.replace('_', ':')
            self.add_method(objc_init_method, name, encoding)
            return objc_init_method
        return decorator

    # Your subclass MUST define a dealloc method, otherwise the
    # association PythonSelf object won't get deleted.
    def dealloc(self, f):
        """Function decorator for dealloc method."""
        def objc_method(objc_self, objc_cmd):
            py_self = self.get_python_self_for_instance(objc_self)
            py_self.objc_cmd = objc_cmd
            f(py_self)
            self.delete_python_self(py_self)
        self.add_method(objc_method, 'dealloc', 'v@:')
        return objc_method        

    def pythonmethod(self, f):
        """Function decorator for python-callable methods."""
        setattr(self.PythonSelf, f.func_name, f)
        return f

######################################################################

# Even though we don't use this directly, it must be loaded so that
# we can find the NSApplication, NSWindow, and NSView classes.
appkit = cdll.LoadLibrary(util.find_library('AppKit'))

NSDefaultRunLoopMode = c_void_p.in_dll(appkit, 'NSDefaultRunLoopMode')
NSEventTrackingRunLoopMode = c_void_p.in_dll(appkit, 'NSEventTrackingRunLoopMode')

# /System/Library/Frameworks/AppKit.framework/Headers/NSEvent.h
NSAnyEventMask = 0xFFFFFFFFL     # NSUIntegerMax

NSKeyDown            = 10
NSKeyUp              = 11
NSFlagsChanged       = 12
NSApplicationDefined = 15

NSAlphaShiftKeyMask         = 1 << 16
NSShiftKeyMask              = 1 << 17
NSControlKeyMask            = 1 << 18
NSAlternateKeyMask          = 1 << 19
NSCommandKeyMask            = 1 << 20
NSNumericPadKeyMask         = 1 << 21
NSHelpKeyMask               = 1 << 22
NSFunctionKeyMask           = 1 << 23

NSInsertFunctionKey   = 0xF727
NSDeleteFunctionKey   = 0xF728
NSHomeFunctionKey     = 0xF729
NSBeginFunctionKey    = 0xF72A
NSEndFunctionKey      = 0xF72B
NSPageUpFunctionKey   = 0xF72C
NSPageDownFunctionKey = 0xF72D

# /System/Library/Frameworks/AppKit.framework/Headers/NSWindow.h
NSBorderlessWindowMask		= 0
NSTitledWindowMask		= 1 << 0
NSClosableWindowMask		= 1 << 1
NSMiniaturizableWindowMask	= 1 << 2
NSResizableWindowMask		= 1 << 3

# /System/Library/Frameworks/AppKit.framework/Headers/NSPanel.h
NSUtilityWindowMask		= 1 << 4

# /System/Library/Frameworks/AppKit.framework/Headers/NSGraphics.h
NSBackingStoreRetained	        = 0
NSBackingStoreNonretained	= 1
NSBackingStoreBuffered	        = 2

# /System/Library/Frameworks/AppKit.framework/Headers/NSTrackingArea.h
NSTrackingMouseEnteredAndExited  = 0x01
NSTrackingMouseMoved             = 0x02
NSTrackingCursorUpdate 		 = 0x04
NSTrackingActiveInActiveApp 	 = 0x40

# /System/Library/Frameworks/AppKit.framework/Headers/NSOpenGL.h
NSOpenGLPFAAllRenderers       =   1   # choose from all available renderers          
NSOpenGLPFADoubleBuffer       =   5   # choose a double buffered pixel format        
NSOpenGLPFAStereo             =   6   # stereo buffering supported                   
NSOpenGLPFAAuxBuffers         =   7   # number of aux buffers                        
NSOpenGLPFAColorSize          =   8   # number of color buffer bits                  
NSOpenGLPFAAlphaSize          =  11   # number of alpha component bits               
NSOpenGLPFADepthSize          =  12   # number of depth buffer bits                  
NSOpenGLPFAStencilSize        =  13   # number of stencil buffer bits                
NSOpenGLPFAAccumSize          =  14   # number of accum buffer bits                  
NSOpenGLPFAMinimumPolicy      =  51   # never choose smaller buffers than requested  
NSOpenGLPFAMaximumPolicy      =  52   # choose largest buffers of type requested     
NSOpenGLPFAOffScreen          =  53   # choose an off-screen capable renderer        
NSOpenGLPFAFullScreen         =  54   # choose a full-screen capable renderer        
NSOpenGLPFASampleBuffers      =  55   # number of multi sample buffers               
NSOpenGLPFASamples            =  56   # number of samples per multi sample buffer    
NSOpenGLPFAAuxDepthStencil    =  57   # each aux buffer has its own depth stencil    
NSOpenGLPFAColorFloat         =  58   # color buffers store floating point pixels    
NSOpenGLPFAMultisample        =  59   # choose multisampling                         
NSOpenGLPFASupersample        =  60   # choose supersampling                         
NSOpenGLPFASampleAlpha        =  61   # request alpha filtering                      
NSOpenGLPFARendererID         =  70   # request renderer by ID                       
NSOpenGLPFASingleRenderer     =  71   # choose a single renderer for all screens     
NSOpenGLPFANoRecovery         =  72   # disable all failure recovery systems         
NSOpenGLPFAAccelerated        =  73   # choose a hardware accelerated renderer       
NSOpenGLPFAClosestPolicy      =  74   # choose the closest color buffer to request   
NSOpenGLPFARobust             =  75   # renderer does not need failure recovery      
NSOpenGLPFABackingStore       =  76   # back buffer contents are valid after swap    
NSOpenGLPFAMPSafe             =  78   # renderer is multi-processor safe             
NSOpenGLPFAWindow             =  80   # can be used to render to an onscreen window  
NSOpenGLPFAMultiScreen        =  81   # single window can span multiple screens      
NSOpenGLPFACompliant          =  83   # renderer is opengl compliant                 
NSOpenGLPFAScreenMask         =  84   # bit mask of supported physical screens       
NSOpenGLPFAPixelBuffer        =  90   # can be used to render to a pbuffer           
NSOpenGLPFARemotePixelBuffer  =  91   # can be used to render offline to a pbuffer   
NSOpenGLPFAAllowOfflineRenderers = 96 # allow use of offline renderers               
NSOpenGLPFAAcceleratedCompute =  97   # choose a hardware accelerated compute device 
NSOpenGLPFAVirtualScreenCount = 128   # number of virtual screens in this format     

NSOpenGLCPSwapInterval        = 222


# /System/Library/Frameworks/ApplicationServices.framework/Frameworks/...
#     CoreGraphics.framework/Headers/CGImage.h
kCGImageAlphaNone                   = 0
kCGImageAlphaPremultipliedLast      = 1
kCGImageAlphaPremultipliedFirst     = 2
kCGImageAlphaLast                   = 3
kCGImageAlphaFirst                  = 4
kCGImageAlphaNoneSkipLast           = 5
kCGImageAlphaNoneSkipFirst          = 6
kCGImageAlphaOnly                   = 7

kCGBitmapAlphaInfoMask              = 0x1F
kCGBitmapFloatComponents            = 1 << 8

kCGBitmapByteOrderMask              = 0x7000
kCGBitmapByteOrderDefault           = 0 << 12
kCGBitmapByteOrder16Little          = 1 << 12
kCGBitmapByteOrder32Little          = 2 << 12
kCGBitmapByteOrder16Big             = 3 << 12
kCGBitmapByteOrder32Big             = 4 << 12

# NSApplication.h
NSApplicationPresentationDefault = 0
NSApplicationPresentationHideDock = 1 << 1
NSApplicationPresentationHideMenuBar = 1 << 3
NSApplicationPresentationDisableProcessSwitching = 1 << 5
NSApplicationPresentationDisableHideApplication = 1 << 8

######################################################################

quartz = cdll.LoadLibrary(util.find_library('quartz'))

CGDirectDisplayID = c_uint32     # CGDirectDisplay.h
CGError = c_int32                # CGError.h

# /System/Library/Frameworks/ApplicationServices.framework/Frameworks/...
#     ImageIO.framework/Headers/CGImageProperties.h
kCGImagePropertyGIFDictionary = c_void_p.in_dll(quartz, 'kCGImagePropertyGIFDictionary')
kCGImagePropertyGIFDelayTime = c_void_p.in_dll(quartz, 'kCGImagePropertyGIFDelayTime')

# /System/Library/Frameworks/ApplicationServices.framework/Frameworks/...
#     CoreGraphics.framework/Headers/CGColorSpace.h
kCGRenderingIntentDefault = 0

quartz.CGDisplayIDToOpenGLDisplayMask.restype = c_uint32
quartz.CGDisplayIDToOpenGLDisplayMask.argtypes = [c_uint32]

quartz.CGMainDisplayID.restype = c_uint32

quartz.CGShieldingWindowLevel.restype = c_int32

quartz.CGCursorIsVisible.restype = c_bool

quartz.CGDisplayCopyAllDisplayModes.restype = c_void_p
quartz.CGDisplayCopyAllDisplayModes.argtypes = [CGDirectDisplayID, c_void_p]

quartz.CGDisplayModeGetRefreshRate.restype = c_double
quartz.CGDisplayModeGetRefreshRate.argtypes = [c_void_p]

quartz.CGDisplayModeCopyPixelEncoding.restype = c_void_p
quartz.CGDisplayModeCopyPixelEncoding.argtypes = [c_void_p]

quartz.CGGetActiveDisplayList.restype = CGError
quartz.CGGetActiveDisplayList.argtypes = [c_uint32, POINTER(CGDirectDisplayID), POINTER(c_uint32)]

quartz.CGDisplayBounds.restype = CGRect
quartz.CGDisplayBounds.argtypes = [CGDirectDisplayID]

quartz.CGImageSourceCreateWithData.restype = c_void_p
quartz.CGImageSourceCreateWithData.argtypes = [c_void_p, c_void_p]

quartz.CGImageSourceCreateImageAtIndex.restype = c_void_p
quartz.CGImageSourceCreateImageAtIndex.argtypes = [c_void_p, c_size_t, c_void_p]

quartz.CGImageSourceCopyPropertiesAtIndex.restype = c_void_p
quartz.CGImageSourceCopyPropertiesAtIndex.argtypes = [c_void_p, c_size_t, c_void_p]

quartz.CGImageGetDataProvider.restype = c_void_p
quartz.CGImageGetDataProvider.argtypes = [c_void_p]

quartz.CGDataProviderCopyData.restype = c_void_p
quartz.CGDataProviderCopyData.argtypes = [c_void_p]

quartz.CGDataProviderCreateWithCFData.restype = c_void_p
quartz.CGDataProviderCreateWithCFData.argtypes = [c_void_p]

quartz.CGImageCreate.restype = c_void_p
quartz.CGImageCreate.argtypes = [c_size_t, c_size_t, c_size_t, c_size_t, c_size_t, c_void_p, c_uint32, c_void_p, c_void_p, c_bool, c_int]

quartz.CGColorSpaceCreateDeviceRGB.restype = c_void_p

quartz.CGDataProviderRelease.restype = None
quartz.CGDataProviderRelease.argtypes = [c_void_p]

quartz.CGColorSpaceRelease.restype = None
quartz.CGColorSpaceRelease.argtypes = [c_void_p]

quartz.CGWarpMouseCursorPosition.restype = CGError
quartz.CGWarpMouseCursorPosition.argtypes = [CGPoint]

quartz.CGDisplayMoveCursorToPoint.restype = CGError
quartz.CGDisplayMoveCursorToPoint.argtypes = [CGDirectDisplayID, CGPoint]

quartz.CGAssociateMouseAndMouseCursorPosition.restype = CGError
quartz.CGAssociateMouseAndMouseCursorPosition.argtypes = [c_bool]

######################################################################

foundation = cdll.LoadLibrary(util.find_library('Foundation'))
foundation.NSMouseInRect.restype = c_bool
foundation.NSMouseInRect.argtypes = [NSPoint, NSRect, c_bool]
