import sys
import os
import inspect

import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
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

    def test_line_macros(self):
        # (blank)
        line = Line('')
        self.assertIsNone(line.macro)

        # (no macro)
        line = Line('G02 X10.75 Y47.44 I-0.11 J-1.26 F70 (blah blah)')
        self.assertIsNone(line.macro)

        # %
        line = Line('%')
        self.assertEqual(str(line.macro), '%')

        # %%
        line = Line('%%')
        self.assertEqual(str(line.macro), '%%')

        # % blah blah %
        line = Line('% blah blah %')
        self.assertEqual(str(line.macro), '% blah blah %')

        # Combined at end of line (not sure if this is legit)
        line = Line('G02 X10.75 Y2 ; abc %something%')
        self.assertEqual(line.comment.text.strip(), 'abc')
        self.assertEqual(line.macro, '%something%')
