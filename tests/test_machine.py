import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode.machine import Position, Machine
from pygcode.line import Line
from pygcode.exceptions import MachineInvalidAxis
from pygcode.gcodes import (
    GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode,
    GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode,
    GCodeCannedCycleReturnPrevLevel, GCodeCannedCycleReturnToR,
)


class PositionTests(unittest.TestCase):
    def test_basics(self):
        p = Position()
        #

    def test_default_axes(self):
        p = Position()  # no instantiation parameters
        # all initialized to zero
        for axis in 'XYZABCUVW':
            self.assertEqual(getattr(p, axis), 0)

        for axis in 'XYZABCUVW':
            # set to 100
            setattr(p, axis, 100)
            self.assertEqual(getattr(p, axis), 100)
            for inner_axis in set('XYZABCUVW') - {axis}:  # no other axis has changed
                self.assertEqual(getattr(p, inner_axis), 0), "axis '%s'" % inner_axis
            # revert back to zero
            setattr(p, axis, 0)
            self.assertEqual(getattr(p, axis), 0)

    # Equality
    def test_equality(self):
        p1 = Position(axes='XYZ', X=1, Y=2)
        p2 = Position(axes='XYZ', X=1, Y=2, Z=0)
        p3 = Position(axes='XYZ', X=1, Y=2, Z=1000)
        p4 = Position(axes='XYZA', X=1, Y=2, Z=0)

        # p1 <--> p2
        self.assertTrue(p1 == p2)
        self.assertFalse(p1 != p2)  # negative case

        # p2 <--> p3
        self.assertTrue(p2 != p3)
        self.assertFalse(p2 == p3)  # negative case

        # p2 <--> p4
        self.assertTrue(p2 != p4)
        self.assertFalse(p2 == p4)  # negative case

    # Arithmetic
    def test_arithmetic_add(self):
        p1 = Position(axes='XYZ', X=1, Y=2)
        p2 = Position(axes='XYZ', Y=10, Z=-20)
        self.assertEqual(p1 + p2, Position(axes='XYZ', X=1, Y=12, Z=-20))

        p3 = Position(axes='XYZA')
        with self.assertRaises(MachineInvalidAxis):
            p1 + p3  # mismatched axes
        with self.assertRaises(MachineInvalidAxis):
            p3 + p1  # mismatched axes

    def test_arithmetic_sub(self):
        p1 = Position(axes='XYZ', X=1, Y=2)
        p2 = Position(axes='XYZ', Y=10, Z=-20)
        self.assertEqual(p1 - p2, Position(axes='XYZ', X=1, Y=-8, Z=20))

        p3 = Position(axes='XYZA')
        p3 - p1  # fine
        with self.assertRaises(MachineInvalidAxis):
            p1 - p3  # mismatched axes

    def test_arithmetic_multiply(self):
        p = Position(axes='XYZ', X=2, Y=10)
        self.assertEqual(p * 2, Position(axes='XYZ', X=4, Y=20))

    def test_arithmetic_divide(self):
        p = Position(axes='XYZ', X=2, Y=10)
        self.assertEqual(p / 2, Position(axes='XYZ', X=1, Y=5))


class MachineGCodeProcessingTests(unittest.TestCase):
    def assert_processed_lines(self, line_data, machine):
        """
        Process lines & assert machine's position
        :param line_data: list of tuples [('g1 x2', {'X':2}), ... ]
        """
        for (i, (line_str, expected_pos)) in enumerate(line_data):
            line = Line(line_str)
            if line.block:
                machine.process_block(line.block)
            # Assert possition change correct
            if expected_pos is not None:
                p1 = machine.pos
                p2 = machine.Position(**expected_pos)
                self.assertEqual(p1, p2, "index:%i '%s': %r != %r" % (i, line_str, p1, p2))

    # Rapid Movement
    def test_rapid_abs(self):
        m = Machine()
        m.process_gcodes(GCodeAbsoluteDistanceMode())
        line_data = [
            ('', {}),  # start @ 0,0,0
            ('g0 x0 y10',       {'X':0, 'Y':10}),
            ('   x10 y10',      {'X':10, 'Y':10}),
            ('   x10 y0',       {'X':10, 'Y':0}),
            ('   x0 y0',        {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    def test_rapid_inc(self):
        m = Machine()
        m.process_gcodes(GCodeIncrementalDistanceMode())
        line_data = [
            ('', {}),  # start @ 0,0,0
            ('g0 y10',  {'X':0, 'Y':10}),
            ('   x10',  {'X':10, 'Y':10}),
            ('   y-10', {'X':10, 'Y':0}),
            ('   x-10', {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    # Linearly Interpolated Movement
    def test_linear_abs(self):
        m = Machine()
        m.process_gcodes(GCodeAbsoluteDistanceMode())
        line_data = [
            ('g1 x0 y10',       {'X':0, 'Y':10}),
            ('   x10 y10',      {'X':10, 'Y':10}),
            ('   x10 y0',       {'X':10, 'Y':0}),
            ('   x0 y0',        {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    def test_linear_inc(self):
        m = Machine()
        m.process_gcodes(GCodeIncrementalDistanceMode())
        line_data = [
            ('g1 y10',  {'X':0, 'Y':10}),
            ('   x10',  {'X':10, 'Y':10}),
            ('   y-10', {'X':10, 'Y':0}),
            ('   x-10', {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    # Arc Movement
    def test_arc_abs(self):
        m = Machine()
        m.process_gcodes(
            GCodeAbsoluteDistanceMode(),
            GCodeIncrementalArcDistanceMode(),
        )
        line_data = [
            # Clockwise circle in 4 segments
            ('g2 x0 y10 i5 j5', {'X':0, 'Y':10}),
            ('   x10 y10 i5 j-5', {'X':10, 'Y':10}),
            ('   x10 y0 i-5 j-5', {'X':10, 'Y':0}),
            ('   x0 y0 i-5 j5', {'X':0, 'Y':0}),
            # Counter-clockwise circle in 4 segments
            ('g3 x10 y0 i5 j5', {'X':10, 'Y':0}),
            ('   x10 y10 i-5 j5', {'X':10, 'Y':10}),
            ('   x0 y10 i-5 j-5', {'X':0, 'Y':10}),
            ('   x0 y0 i5 j-5', {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    def test_arc_inc(self):
        m = Machine()
        m.process_gcodes(
            GCodeIncrementalDistanceMode(),
            GCodeIncrementalArcDistanceMode(),
        )
        line_data = [
            # Clockwise circle in 4 segments
            ('g2 y10 i5 j5', {'X':0, 'Y':10}),
            ('   x10 i5 j-5', {'X':10, 'Y':10}),
            ('   y-10 i-5 j-5', {'X':10, 'Y':0}),
            ('   x-10 i-5 j5', {'X':0, 'Y':0}),
            # Counter-clockwise circle in 4 segments
            ('g3 x10 i5 j5', {'X':10, 'Y':0}),
            ('   y10 i-5 j5', {'X':10, 'Y':10}),
            ('   x-10 i-5 j-5', {'X':0, 'Y':10}),
            ('   y-10 i5 j-5', {'X':0, 'Y':0}),
        ]
        self.assert_processed_lines(line_data, m)

    # Canned Drilling Cycles
    def test_canned_return2oldz(self):
        m = Machine()
        m.process_gcodes(
            GCodeAbsoluteDistanceMode(),
            GCodeCannedCycleReturnPrevLevel(),
        )
        line_data = [
            ('g0 z5', {'Z':5}),
            ('g81 x10 y20 z-2 r1', {'X':10, 'Y':20, 'Z':5}),
        ]
        self.assert_processed_lines(line_data, m)

    def test_canned_return2r(self):
        m = Machine()
        m.process_gcodes(
            GCodeAbsoluteDistanceMode(),
            GCodeCannedCycleReturnToR(),
        )
        line_data = [
            ('g0 z5', {'Z':5}),
            ('g81 x10 y20 z-2 r1', {'X':10, 'Y':20, 'Z':1}),
        ]
        self.assert_processed_lines(line_data, m)

    def test_canned_loops(self):
        m = Machine()
        m.process_gcodes(
            GCodeAbsoluteDistanceMode(),
            GCodeCannedCycleReturnPrevLevel(),
        )
        line_data = [
            ('g0 z5', None),
            ('g81 x10 y20 z-2 r1 l2', {'X':10, 'Y':20, 'Z':5}),
            ('g91', None),  # switch to incremental mode
            ('g81 x10 y20 z-2 r1 l2', {'X':30, 'Y':60, 'Z':5}),
        ]
        self.assert_processed_lines(line_data, m)
