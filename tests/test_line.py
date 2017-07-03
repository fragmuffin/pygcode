import sys
import os
import inspect

import unittest

# Units Under Test
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.join(_this_path, '..'))
from pygcode.line import Line


class LineCommentTests(unittest.TestCase):
    def test_line_comment_semicolon(self):
        line = Line('G02 X10.75 Y47.44 I-0.11 J-1.26 F70 ; blah blah')
        self.assertEqual(line.comment.text, 'blah blah')
        self.assertEqual(len(line.block.words), 6)

    def test_line_comment_brackets(self):
        line = Line('G02 X10.75 Y47.44 I-0.11 J-1.26 F70 (blah blah)')
        self.assertEqual(line.comment.text, 'blah blah')
        self.assertEqual(len(line.block.words), 6)

    def test_line_comment_brackets_multi(self):
        line = Line('G02 X10.75 (x coord) Y47.44 (y coord) I-0.11 J-1.26 F70 (eol)')
        self.assertEqual(line.comment.text, 'x coord. y coord. eol')
        self.assertEqual(len(line.block.words), 6)
