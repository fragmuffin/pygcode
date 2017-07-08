import sys
import os
import inspect

import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode import words


class WordIterTests(unittest.TestCase):
    def test_iter1(self):
        block_str = 'G01 Z-0.5 F100'
        w = list(words.text2words(block_str))
        # word length
        self.assertEqual(len(w), 3)
        # word values
        self.assertEqual(w[0], words.Word('G', 1))
        self.assertEqual(w[1], words.Word('Z', -0.5))
        self.assertEqual(w[2], words.Word('F', 100))

    def test_iter2(self):
        block_str = 'G02 X10.75 Y47.44 I-0.11 J-1.26 F70'
        w = list(words.text2words(block_str))
        # word length
        self.assertEqual(len(w), 6)
        # word values
        self.assertEqual([w[0].letter, w[0].value], ['G', 2])
        self.assertEqual([w[1].letter, w[1].value], ['X', 10.75])
        self.assertEqual([w[2].letter, w[2].value], ['Y', 47.44])
        self.assertEqual([w[3].letter, w[3].value], ['I', -0.11])
        self.assertEqual([w[4].letter, w[4].value], ['J', -1.26])
        self.assertEqual([w[5].letter, w[5].value], ['F', 70])


class WordValueMatchTests(unittest.TestCase):

    def regex_assertions(self, regex, positive_list, negative_list):
        # Assert all elements of positive_list match regex
        for (value_str, expected_match) in positive_list:
            match = regex.search(value_str)
            self.assertIsNotNone(match, "failed to match '%s'" % value_str)
            self.assertEqual(match.group(), expected_match)

        # Asesrt all elements of negative_list do not match regex
        for value_str in negative_list:
            match = regex.search(value_str)
            self.assertIsNone(match, "matched for '%s'" % value_str)

    def test_float(self):
        self.regex_assertions(
            regex=words.REGEX_FLOAT,
            positive_list=[
                ('1.2', '1.2'), ('1', '1'), ('200', '200'), ('0092', '0092'),
                ('1.', '1.'), ('.2', '.2'), ('-1.234', '-1.234'),
                ('-1.', '-1.'), ('-.289', '-.289'),
                # error cases (only detectable in gcode context)
                ('1.2e3', '1.2'),
            ],
            negative_list=['.', ' 1.2']
        )

    def test_code(self):
        self.regex_assertions(
            regex=words.REGEX_CODE,
            positive_list=[
                ('1.2', '1.2'), ('1', '1'), ('10', '10'),
                ('02', '02'), ('02.3', '02.3'),
                ('1.', '1'), ('03 ', '03'),
                # error cases (only detectable in gcode context)
                ('30.12', '30.1'),
            ],
            negative_list=['.2', '.', ' 2']
        )
