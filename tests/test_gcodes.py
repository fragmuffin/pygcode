import sys
import os
import inspect
import re
import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode import gcodes
from pygcode import words
from pygcode import machine

from pygcode.exceptions import GCodeWordStrError

class GCodeWordMappingTests(unittest.TestCase):
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

class GCodeModalGroupTests(unittest.TestCase):
    def test_modal_groups(self):
        # Modal groups taken (and slightly modified) from LinuxCNC documentation:
        #   link: http://linuxcnc.org/docs/html/gcode/overview.html#_modal_groups
        table_rows = ''
        #                 Table 5. G-Code Modal Groups
        #       MODAL GROUP MEANING                     MEMBER WORDS
        table_rows += '''
        Non-modal codes (Group 0)               G4,G10,G28,G30,G53,G92,G92.1,G92.2,G92.3
        Motion (Group 1)                        G0,G1,G2,G3,G33,G38.2,G38.3,G38.4
        Motion (Group 1)                        G38.5,G73,G76,G81,G82,G83,G85,G89
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
                    word = list(words.text2words(word_str))[0]
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


class Words2GCodesTests(unittest.TestCase):
    def test_stuff(self):  # FIXME: function name
        line = 'G1 X82.6892 Y-38.6339 F1500'
        word_list = list(words.text2words(line))
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


class Text2GCodesTests(unittest.TestCase):
    def test_basic(self):
        gcs = gcodes.text2gcodes('G1 X1 Y2 G90')
        self.assertEqual(len(gcs), 2)
        # G1 X1 Y2
        self.assertEqual(gcs[0].word, words.Word('G', 1))
        self.assertEqual(gcs[0].X, 1)
        self.assertEqual(gcs[0].Y, 2)
        # G90
        self.assertEqual(gcs[1].word, words.Word('G', 90))

    def test_modal_params(self):
        with self.assertRaises(GCodeWordStrError):
            gcodes.text2gcodes('X1 Y2')


class GCodeSplitTests(unittest.TestCase):

    def test_split(self):
        g_list = gcodes.text2gcodes('G91 S1000 G1 X1 Y2 M3')
        split = gcodes.split_gcodes(g_list, gcodes.GCodeStartSpindle)
        self.assertEqual([len(x) for x in split], [1, 1, 2])
        self.assertTrue(any(isinstance(g, gcodes.GCodeSpindleSpeed) for g in split[0]))
        self.assertTrue(isinstance(split[1][0], gcodes.GCodeStartSpindle))
        self.assertTrue(any(isinstance(g, gcodes.GCodeDistanceMode) for g in split[2]))
        self.assertTrue(any(isinstance(g, gcodes.GCodeMotion) for g in split[2]))

    def test_split_unsorted(self):
        g_list = gcodes.text2gcodes('G91 G1 X1 Y2 M3 S1000')
        split = gcodes.split_gcodes(g_list, gcodes.GCodeStartSpindle, sort_list=False)
        self.assertEqual([len(x) for x in split], [2, 1, 1])
        self.assertTrue(any(isinstance(g, gcodes.GCodeDistanceMode) for g in split[0]))
        self.assertTrue(any(isinstance(g, gcodes.GCodeMotion) for g in split[0]))
        self.assertTrue(isinstance(split[1][0], gcodes.GCodeStartSpindle))
        self.assertTrue(any(isinstance(g, gcodes.GCodeSpindleSpeed) for g in split[2]))


class GCodeAbsoluteToRelativeDecoratorTests(unittest.TestCase):

    def test_gcodes_abs2rel(self):
        # setup gcode testlist
        L = gcodes.GCodeLinearMove
        R = gcodes.GCodeRapidMove
        args = lambda x, y, z: dict(a for a in zip('XYZ', [x,y,z]) if a[1] is not None)
        gcode_list = [
            # GCode instances    Expected incremental output
            (L(**args(0, 0, 0)), L(**args(-10, -20, -30))),
            (L(**args(1, 2, 0)), L(**args(1, 2, None))),
            (L(**args(3, 4, 0)), L(**args(2, 2, None))),
            (R(**args(1, 2, 0)), R(**args(-2, -2, None))),
            (R(**args(3, 4, 0)), R(**args(2, 2, None))),
            (L(**args(3, 4, 0)), None),
            (L(**args(3, 4, 8)), L(**args(None, None, 8))),
        ]

        m = machine.Machine()

        # Incremental Output
        m.set_mode(gcodes.GCodeAbsoluteDistanceMode())
        m.move_to(X=10, Y=20, Z=30)  # initial position (absolute)
        m.set_mode(gcodes.GCodeIncrementalDistanceMode())

        @gcodes._gcodes_abs2rel(m.pos, dist_mode=m.mode.distance, axes=m.axes)
        def expecting_rel():
            return [g[0] for g in gcode_list]

        trimmed_expecting_list = [x[1] for x in gcode_list if x[1] is not None]
        for (i, g) in enumerate(expecting_rel()):
            expected = trimmed_expecting_list[i]
            self.assertEqual(type(g), type(expected))
            self.assertEqual(g.word, expected.word)
            self.assertEqual(g.params, expected.params)

        # Absolute Output
        m.set_mode(gcodes.GCodeAbsoluteDistanceMode())
        m.move_to(X=10, Y=20, Z=30)  # initial position

        @gcodes._gcodes_abs2rel(m.pos, dist_mode=m.mode.distance, axes=m.axes)
        def expecting_abs():
            return [g[0] for g in gcode_list]

        for (i, g) in enumerate(expecting_abs()):
            expected = gcode_list[i][0]  # expecting passthrough
            self.assertEqual(type(g), type(expected))
            self.assertEqual(g.word, expected.word)
            self.assertEqual(g.params, expected.params)
