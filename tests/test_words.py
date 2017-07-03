import sys
import os
import inspect

import unittest

# Units Under Test
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.join(_this_path, '..'))
import pygcode.words as gcode_words

#words.iter_words

class WordTests(unittest.TestCase):
    def test_O(self):
        pass # TODO



class WordIterTests(unittest.TestCase):
    def test_iter1(self):
        block_str = 'G01 Z-0.5 F100'
        w = list(gcode_words.iter_words(block_str))
        # word length
        self.assertEqual(len(w), 3)
        # word values
        self.assertEqual([w[0].letter, w[0].value], ['G', '01'])
        self.assertEqual([w[1].letter, w[1].value], ['Z', -0.5])
        self.assertEqual([w[2].letter, w[2].value], ['F', 100])

    def test_iter2(self):
        block_str = 'G02 X10.75 Y47.44 I-0.11 J-1.26 F70'
        w = list(gcode_words.iter_words(block_str))
        # word length
        self.assertEqual(len(w), 6)
        # word values
        self.assertEqual([w[0].letter, w[0].value], ['G', '02'])
        self.assertEqual([w[1].letter, w[1].value], ['X', 10.75])
        self.assertEqual([w[2].letter, w[2].value], ['Y', 47.44])
        self.assertEqual([w[3].letter, w[3].value], ['I', -0.11])
        self.assertEqual([w[4].letter, w[4].value], ['J', -1.26])
        self.assertEqual([w[5].letter, w[5].value], ['F', 70])
