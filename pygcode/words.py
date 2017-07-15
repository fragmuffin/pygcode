import re
import itertools
import six

from .exceptions import GCodeBlockFormatError, GCodeWordStrError

REGEX_FLOAT = re.compile(r'^-?(\d+\.?\d*|\.\d+)') # testcase: ..tests.test_words.WordValueMatchTests.test_float
REGEX_INT = re.compile(r'^-?\d+')
REGEX_POSITIVEINT = re.compile(r'^\d+')
REGEX_CODE = re.compile(r'^\d+(\.\d)?') # similar

# Value cleaning functions
def _clean_codestr(value):
    if value < 10:
        return "0%g" % value
    return "%g" % value

CLEAN_NONE = lambda v: v
CLEAN_FLOAT = lambda v: "{0:g}".format(round(v, 3))
CLEAN_CODE = _clean_codestr
CLEAN_INT = lambda v: "%g" % v

WORD_MAP = {
    # Descriptions copied from wikipedia:
    #   https://en.wikipedia.org/wiki/G-code#Letter_addresses

    # Rotational Axes
    'A': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of A axis (rotational axis around X axis)",
        'clean_value': CLEAN_FLOAT,
    },
    'B': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of B axis (rotational axis around Y axis)",
        'clean_value': CLEAN_FLOAT,
    },
    'C': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of C axis (rotational axis around Z axis)",
        'clean_value': CLEAN_FLOAT,
    },
    'D': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines diameter or radial offset used for cutter compensation. D is used for depth of cut on lathes. It is used for aperture selection and commands on photoplotters.",
        'clean_value': CLEAN_FLOAT,
    },
    # Feed Rates
    'E': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Precision feedrate for threading on lathes",
        'clean_value': CLEAN_FLOAT,
    },
    'F': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Feedrate",
        'clean_value': CLEAN_FLOAT,
    },
    # G-Codes
    'G': {
        'class': float,
        'value_regex': REGEX_CODE,
        'description': "Address for preparatory commands",
        'clean_value': CLEAN_CODE,
    },
    # Tool Offsets
    'H': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines tool length offset; Incremental axis corresponding to C axis (e.g., on a turn-mill)",
        'clean_value': CLEAN_FLOAT,
    },
    # Arc radius center coords
    'I': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines arc center in X axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        'clean_value': CLEAN_FLOAT,
    },
    'J': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines arc center in Y axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        'clean_value': CLEAN_FLOAT,
    },
    'K': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines arc center in Z axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles, equal to L address.",
        'clean_value': CLEAN_FLOAT,
    },
    # Loop Count
    'L': {
        'class': int,
        'value_regex': REGEX_POSITIVEINT,
        'description': "Fixed cycle loop count; Specification of what register to edit using G10",
        'clean_value': CLEAN_INT,
    },
    # Miscellaneous Function
    'M': {
        'class': float,
        'value_regex': REGEX_CODE,
        'description': "Miscellaneous function",
        'clean_value': CLEAN_CODE,
    },
    # Line Number
    'N': {
        'class': int,
        'value_regex': REGEX_POSITIVEINT,
        'description': "Line (block) number in program; System parameter number to change using G10",
        'clean_value': CLEAN_INT,
    },
    # Program Name
    'O': {
        'class': str,
        'value_regex': re.compile(r'^.+$'), # all the way to the end
        'description': "Program name",
        'clean_value': CLEAN_NONE,
    },
    # Parameter (arbitrary parameter)
    'P': {
        'class': float, # parameter is often an integer, but can be a float
        'value_regex': REGEX_FLOAT,
        'description': "Serves as parameter address for various G and M codes",
        'clean_value': CLEAN_FLOAT,
    },
    # Peck increment
    'Q': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Depth to increase on each peck; Peck increment in canned cycles",
        'clean_value': CLEAN_FLOAT,
    },
    # Arc Radius
    'R': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines size of arc radius, or defines retract height in milling canned cycles",
        'clean_value': CLEAN_FLOAT,
    },
    # Spindle speed
    'S': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Defines speed, either spindle speed or surface speed depending on mode",
        'clean_value': CLEAN_FLOAT,
    },
    # Tool Selecton
    'T': {
        'class': str,
        'value_regex': REGEX_POSITIVEINT, # tool string may have leading '0's, but is effectively an index (integer)
        'description': "Tool selection",
        'clean_value': CLEAN_NONE,
    },
    # Incremental axes
    'U': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Incremental axis corresponding to X axis (typically only lathe group A controls) Also defines dwell time on some machines (instead of 'P' or 'X').",
        'clean_value': CLEAN_FLOAT,
    },
    'V': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Incremental axis corresponding to Y axis",
        'clean_value': CLEAN_FLOAT,
    },
    'W': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Incremental axis corresponding to Z axis (typically only lathe group A controls)",
        'clean_value': CLEAN_FLOAT,
    },
    # Linear Axes
    'X': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of X axis.",
        'clean_value': CLEAN_FLOAT,
    },
    'Y': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of Y axis.",
        'clean_value': CLEAN_FLOAT,
    },
    'Z': {
        'class': float,
        'value_regex': REGEX_FLOAT,
        'description': "Absolute or incremental position of Z axis.",
        'clean_value': CLEAN_FLOAT,
    },
}


class Word(object):
    def __init__(self, *args):
        if len(args) not in (1, 2):
            raise AssertionError("input arguments either: (letter, value) or (word_str)")
        if len(args) == 2:
            # Word('G', 90)
            (letter, value) = args
        else:
            # Word('G90')
            letter = args[0][0] # first letter
            value = args[0][1:] # rest of string
        letter = letter.upper()

        self._value_class = WORD_MAP[letter]['class']
        self._value_clean = WORD_MAP[letter]['clean_value']

        self.letter = letter
        self.value = value

    def __str__(self):
        return "{letter}{value}".format(
            letter=self.letter,
            value=self.value_str,
        )

    def __repr__(self):
        return "<{class_name}: {string}>".format(
            class_name=self.__class__.__name__,
            string=str(self),
        )

    # Sorting
    def __lt__(self, other):
        return (self.letter, self.value) < (other.letter, other.value)

    def __gt__(self, other):
        return (self.letter, self.value) > (other.letter, other.value)

    def __le__(self, other):
        return (self.letter, self.value) <= (other.letter, other.value)

    def __ge__(self, other):
        return (self.letter, self.value) >= (other.letter, other.value)

    # Equality
    def __eq__(self, other):
        if isinstance(other, six.string_types):
            other = str2word(other)
        return (self.letter == other.letter) and (self.value == other.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    # Hashing
    def __hash__(self):
        return hash((self.letter, self.value))

    @property
    def value_str(self):
        """Clean string representation, for consistent file output"""
        return self._value_clean(self.value)

    # Value Properties
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = self._value_class(new_value)

    @property
    def description(self):
        return "%s: %s" % (self.letter, WORD_MAP[self.letter]['description'])


def text2words(block_text):
    """
    Iterate through block text yielding Word instances
    :param block_text: text for given block with comments removed
    """
    next_word = re.compile(r'^.*?(?P<letter>[%s])' % ''.join(WORD_MAP.keys()), re.IGNORECASE)

    index = 0
    while True:
        letter_match = next_word.search(block_text[index:])
        if letter_match:
            # Letter
            letter = letter_match.group('letter').upper()
            index += letter_match.end() # propogate index to start of value

            # Value
            value_regex = WORD_MAP[letter]['value_regex']
            value_match = value_regex.search(block_text[index:])
            if value_match is None:
                raise GCodeWordStrError("word '%s' value invalid" % letter)
            value = value_match.group() # matched text

            yield Word(letter, value)

            index += value_match.end() # propogate index to end of value
        else:
            break

    remainder = block_text[index:]
    if remainder and re.search(r'\S', remainder):
        raise GCodeWordStrError("block code remaining '%s'" % remainder)


def str2word(word_str):
    words = list(text2words(word_str))
    if words:
        if len(words) > 1:
            raise GCodeWordStrError("more than one word given")
        return words[0]
    return None


def words2dict(word_list, limit_word_letters=None):
    """
    Represent a list of words as a dict
    :param limit_word_letters: iterable containing a white-list of word letters (None allows all)
    :return: dict of the form: {<letter>: <value>, ... }
    """
    # Remember: duplicate word letters cannot be represented as a dict
    return dict(
        (w.letter, w.value) for w in word_list
        if (limit_word_letters is None) or (w.letter in limit_word_letters)
    )
