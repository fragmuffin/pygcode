import unittest
import re

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode.utils import omit_redundant_modes
from pygcode import text2gcodes, Line

class UtilityTests(unittest.TestCase):
    def test_omit_redundant_modes(self):
        lines = [
            Line(line_str)
            for line_str in re.split(r'\s*\n\s*', '''
                g1 x0 y0 ; yes
                g1 x10 y-20 ; no
                g0 x-3 y2 ; yes
                g0 x0 y0 ; no
                g0 x1 y1 ; no
                g1 x20 y20 z5 ; yes
            ''')
            if line_str
        ]
        gcodes = [l.gcodes[0] for l in lines]
        comments = [l.comment for l in lines]
        for (i, g) in enumerate(omit_redundant_modes(gcodes)):
            comment = comments[i].text if comments[i] else None
            if comment == 'no':
                self.assertIsNotNone(re.search(r'^\s', str(g)))
            elif comment == 'yes':
                self.assertIsNone(re.search(r'^\s', str(g)))
