import sys
import os
import inspect

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

class TestWordsToGCodes(unittest.TestCase):
    def test_stuff(self):  # FIXME: function name
        line = 'G1 X82.6892 Y-38.6339 F1500'
        word_list = list(words.iter_words(line))
        result = gcodes.words_to_gcodes(word_list)
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
