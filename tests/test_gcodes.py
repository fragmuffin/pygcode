import sys
import os
import inspect
import re
import unittest

# Units Under Test
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.join(_this_path, '..'))
from pygcode import gcodes
from pygcode import words
class TestGCodeWordMapping(unittest.TestCase):
    def test_word_map_integrity(self):

        gcodes.build_maps()
        for (word_maches, fn_class) in gcodes._gcode_function_list:
            for (word, key_class) in gcodes._gcode_word_map.items():
                # Verify that no mapped word will yield a True result
                #   from any of the 'word_maches' functions
                self.assertFalse(
                    word_maches(word),
                    "conflict with %s and %s" % (fn_class, key_class)
                )

class TestGCodeModalGroups(unittest.TestCase):
    def test_modal_groups(self):
        # Modal groups taken (and slightly modified) from LinuxCNC documentation:
        #   link: http://linuxcnc.org/docs/html/gcode/overview.html#_modal_groups
        table_rows = ''
        #                 Table 5. G-Code Modal Groups
        #       MODAL GROUP MEANING                     MEMBER WORDS
        table_rows += '''
        Non-modal codes (Group 0)               G4,G10,G28,G30,G53,G92,G92.1,G92.2,G92.3
        Motion (Group 1)                        G0,G1,G2,G3,G33,G38.2,G38.3,G38.4
        Motion (Group 1)                        G38.5,G73,G76,G80,G81,G82,G83,G85,G89
        Plane selection (Group 2)               G17, G18, G19, G17.1, G18.1, G19.1
        Distance Mode (Group 3)                 G90, G91
        Arc IJK Distance Mode (Group 4)         G90.1, G91.1
        Feed Rate Mode (Group 5)                G93, G94, G95
        Units (Group 6)                         G20, G21
        Cutter Diameter Compensation (Group 7)  G40, G41, G42, G41.1, G42.1
        Tool Length Offset (Group 8)            G43, G43.1, G49
        Canned Cycles Return Mode (Group 10)    G98
        Coordinate System (Group 12)            G54,G55,G56,G57,G58,G59,G59.1,G59.2,G59.3
        Control Mode (Group 13)                 G61, G61.1, G64
        Spindle Speed Mode (Group 14)           G96, G97
        Lathe Diameter Mode (Group 15)          G7,G8
        '''

        #                 Table 6. M-Code Modal Groups
        #       MODAL GROUP MEANING                     MEMBER WORDS
        table_rows += re.sub(r'\(Group (\d+)\)', r'(Group 10\1)', '''
        Stopping (Group 4)                      M0, M1, M2, M30, M60
        Spindle (Group 7)                       M3, M4, M5
        Coolant (Group 8)                       M7, M8, M9
        Override Switches (Group 9)             M48, M49
        ''') # groups += 100 (to distinguish "M" GCodes from "G" GCodes)

        for row in table_rows.split('\n'):
            match = re.search(r'^\s*(?P<title>.*)\s*\(Group (?P<group>\d+)\)\s*(?P<words>.*)$', row, re.I)
            if match:
                for word_str in re.split(r'\s*,\s*', match.group('words')):
                    word = list(words.iter_words(word_str))[0]
                    gcode_class = gcodes.word_gcode_class(word)
                    # GCode class found for each word in the table
                    self.assertIsNotNone(gcode_class)
                    # GCode's modal group equals that defined in the table
                    expected_group = int(match.group('group'))
                    if expected_group == 0:
                        self.assertIsNone(
                            gcode_class.modal_group,
                            "%s modal_group: %s is not None" % (gcode_class, gcode_class.modal_group)
                        )
                    else:
                        self.assertEqual(
                            gcode_class.modal_group, expected_group,
                            "%s != %s (%r)" % (gcode_class.modal_group, expected_group, word)
                        )


class TestWordsToGCodes(unittest.TestCase):
    def test_stuff(self):  # FIXME: function name
        line = 'G1 X82.6892 Y-38.6339 F1500'
        word_list = list(words.iter_words(line))
        result = gcodes.words2gcodes(word_list)
        # result form
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        # result content
        (gcode_list, unused_words) = result
        self.assertEqual(len(gcode_list), 2)
        self.assertEqual(unused_words, [])
        # Parsed GCodes
        #   G1
        self.assertEqual(gcode_list[0].word, words.Word('G', 1))
        self.assertEqual(gcode_list[0].X, 82.6892)
        self.assertEqual(gcode_list[0].Y, -38.6339)
        #   F1500
        self.assertEqual(gcode_list[1].word, words.Word('F', 1500))
