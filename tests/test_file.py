import sys
import os
import inspect

import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode.file import GCodeFile, GCodeParser

class GCodeParserTest(unittest.TestCase):
    FILENAME = 'test-files/vertical-slot.ngc'

    def test_parser(self):
        parser = GCodeParser(self.FILENAME)
        # count lines
        line_count = 0
        for line in parser.iterlines():
            line_count += 1
        self.assertEqual(line_count, 26)
        parser.close()
