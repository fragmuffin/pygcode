import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode.machine import Position, Machine
from pygcode.line import Line


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
        with self.assertRaises(AssertionError):
            p1 + p3  # mismatched axes
        with self.assertRaises(AssertionError):
            p3 + p1  # mismatched axes

    def test_arithmetic_sub(self):
        p1 = Position(axes='XYZ', X=1, Y=2)
        p2 = Position(axes='XYZ', Y=10, Z=-20)
        self.assertEqual(p1 - p2, Position(axes='XYZ', X=1, Y=-8, Z=20))

        p3 = Position(axes='XYZA')
        p3 - p1  # fine
        with self.assertRaises(AssertionError):
            p1 - p3  # mismatched axes

    def test_arithmetic_multiply(self):
        p = Position(axes='XYZ', X=2, Y=10)
        self.assertEqual(p * 2, Position(axes='XYZ', X=4, Y=20))

    def test_arithmetic_divide(self):
        p = Position(axes='XYZ', X=2, Y=10)
        self.assertEqual(p / 2, Position(axes='XYZ', X=1, Y=5))



class MachineGCodeProcessingTests(unittest.TestCase):
    def test_linear_movement(self):
        m = Machine()
        test_str = '''; move in a 10mm square
            F100 M3 S1000   ; 0
            g1 x0 y10       ; 1
            g1 x10 y10      ; 2
            g1 x10 y0       ; 3
            g1 x0 y0        ; 4
        '''
        expected_pos = {
            '0': m.Position(),
            '1': m.Position(X=0, Y=10),
            '2': m.Position(X=10, Y=10),
            '3': m.Position(X=10, Y=0),
            '4': m.Position(X=0, Y=0),
        }
        #print("\n%r\n%r" % (m.mode, m.state))
        for line_text in str_lines(test_str):
            line = Line(line_text)
            if line.block:
                #print("\n%s" % line.block)
                m.process_block(line.block)
                # Assert possition change correct
                comment = line.comment.text
                if comment in expected_pos:
                    self.assertEqual(m.pos, expected_pos[comment])
                #print("%r\n%r\npos=%r" % (m.mode, m.state, m.pos))


#m = Machine()
#
#file = GCodeParser('part1.gcode')
#for line in file.iterlines():
#    for (i, gcode) in enumerate(line.block.gcode):
#        if isinstance(gcode, GCodeArcMove):
#            arc = gcode
#            line_params = arc.line_segments(precision=0.0005)
#            for
