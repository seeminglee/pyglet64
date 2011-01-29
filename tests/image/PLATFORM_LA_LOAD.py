#!/usr/bin/env python

'''Test LA load using the platform decoder (Quartz, GDI+ or Gdk).  You
should see the la.png image on a checkboard background.
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id$'

import unittest
import base_load
import sys

if sys.platform == 'linux2':
    from pyglet.image.codecs.gdkpixbuf2 import GdkPixbuf2ImageDecoder as dclass
elif sys.platform in ('win32', 'cygwin'):
    from pyglet.image.codecs.gdiplus import GDIPlusDecoder as dclass
elif sys.platform == 'darwin':
    from pyglet.image.codecs.quartz import QuartzImageDecoder as dclass

class TEST_PLATFORM_LA_LOAD(base_load.TestLoad):
    texture_file = 'la.png'
    decoder = dclass()

if __name__ == '__main__':
    unittest.main()
