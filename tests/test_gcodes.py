import sys
import os
import inspect

import unittest

# Units Under Test
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.join(_this_path, '..'))
from pygcode import gcodes


class TestGCodeWordMapping(unittest.TestCase):
    def test_word_map_integrity(self):
        gcodes._build_maps()
        for (word_maches, fn_class) in gcodes._gcode_function_list:
            for (word, key_class) in gcodes._gcode_word_map.items():
                # Verify that no mapped word will yield a True result
                #   from any of the 'word_maches' functions
                self.assertFalse(
                    word_maches(word),
                    "conflict with %s and %s" % (fn_class, key_class)
                )
