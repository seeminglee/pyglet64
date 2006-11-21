#!/usr/bin/env python

'''Test DDS DXT5 image load.
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id: $'

import unittest
import base_load

class TEST_DDS_DXT5_LOAD(base_load.TestLoad):
    texture_file = 'dxt5.dds'

if __name__ == '__main__':
    unittest.main()