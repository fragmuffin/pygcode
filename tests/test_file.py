import sys
import os
import inspect

import unittest

# Units Under Test
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.join(_this_path, '..'))
from pygcode.file import parse, GCodeFile

class FileParseTest(unittest.TestCase):
    FILENAME = 'test-files/vertical-slot.ngc'

    def test_parser(self):
        file = parse(self.FILENAME)
        self.assertEqual(len(file.lines), 26)
        # FIXME: just verifying content visually
        #for line in file.lines:
        #    print(line)
