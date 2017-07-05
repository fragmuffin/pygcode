import re
import itertools
import six

from .exceptions import GCodeBlockFormatError


FLOAT_REGEX = re.compile(r'^-?(\d+\.?\d*|\.\d+)') # testcase: ..tests.test_words.WordValueMatchTests.test_float
INT_REGEX = re.compile(r'^-?\d+')
POSITIVEINT_REGEX = re.compile(r'^\d+')
CODE_REGEX = re.compile(r'^\d+(\.\d)?') # similar

WORD_MAP = {
    # Descriptions copied from wikipedia:
    #   https://en.wikipedia.org/wiki/G-code#Letter_addresses

    # Rotational Axes
    'A': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of A axis (rotational axis around X axis)",
    },
    'B': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of B axis (rotational axis around Y axis)",
    },
    'C': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of C axis (rotational axis around Z axis)",
    },
    'D': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines diameter or radial offset used for cutter compensation. D is used for depth of cut on lathes. It is used for aperture selection and commands on photoplotters.",
    },
    # Feed Rates
    'E': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Precision feedrate for threading on lathes",
    },
    'F': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Feedrate",
    },
    # G-Codes
    'G': {
        'class': float,
        'value_regex': CODE_REGEX,
        'description': "Address for preparatory commands",
    },
    # Tool Offsets
    'H': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines tool length offset; Incremental axis corresponding to C axis (e.g., on a turn-mill)",
    },
    # Arc radius center coords
    'I': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines arc center in X axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
    },
    'J': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines arc center in Y axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
    },
    'K': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines arc center in Z axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles, equal to L address.",
    },
    # Loop Count
    'L': {
        'class': int,
        'value_regex': POSITIVEINT_REGEX,
        'description': "Fixed cycle loop count; Specification of what register to edit using G10",
    },
    # Miscellaneous Function
    'M': {
        'class': float,
        'value_regex': CODE_REGEX,
        'description': "Miscellaneous function",
    },
    # Line Number
    'N': {
        'class': int,
        'value_regex': POSITIVEINT_REGEX,
        'description': "Line (block) number in program; System parameter number to change using G10",
    },
    # Program Name
    'O': {
        'class': str,
        'value_regex': re.compile(r'^.+$'), # all the way to the end
        'description': "Program name",
    },
    # Parameter (arbitrary parameter)
    'P': {
        'class': float, # parameter is often an integer, but can be a float
        'value_regex': FLOAT_REGEX,
        'description': "Serves as parameter address for various G and M codes",
    },
    # Peck increment
    'Q': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Depth to increase on each peck; Peck increment in canned cycles",
    },
    # Arc Radius
    'R': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines size of arc radius, or defines retract height in milling canned cycles",
    },
    # Spindle speed
    'S': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Defines speed, either spindle speed or surface speed depending on mode",
    },
    # Tool Selecton
    'T': {
        'class': str,
        'value_regex': POSITIVEINT_REGEX, # tool string may have leading '0's, but is effectively an index (integer)
        'description': "Tool selection",
    },
    # Incremental axes
    'U': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Incremental axis corresponding to X axis (typically only lathe group A controls) Also defines dwell time on some machines (instead of 'P' or 'X').",
    },
    'V': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Incremental axis corresponding to Y axis",
    },
    'W': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Incremental axis corresponding to Z axis (typically only lathe group A controls)",
    },
    # Linear Axes
    'X': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of X axis.",
    },
    'Y': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of Y axis.",
    },
    'Z': {
        'class': float,
        'value_regex': FLOAT_REGEX,
        'description': "Absolute or incremental position of Z axis.",
    },
}


class Word(object):
    def __init__(self, letter, value):
        self.letter = letter.upper()

        self._value_str = None
        self._value = None
        if isinstance(value, six.string_types):
            self._value_str = value
        else:
            self._value = value

        # Sorting Order
        self._order_linuxcnc = None

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

    def __eq__(self, other):
        return (self.letter == other.letter) and (self.value == other.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.letter, self.value))

    # Value Properties
    @property
    def value_str(self):
        """Value string, or """
        if self._value_str is None:
            return str(self._value)
        return self._value_str

    @property
    def value(self):
        if self._value is None:
            return WORD_MAP[self.letter]['class'](self._value_str)
        return self._value

    # Order
    @property
    def orderval_linuxcnc(self):
        if self._order_linuxcnc is None:
            self._order_linuxcnc = _word_order_linuxcnc(self)
        return self._order_linuxcnc

    @property
    def description(self):
        return "%s: %s" % (self.letter, WORD_MAP[self.letter]['description'])

NEXT_WORD = re.compile(r'^.*?(?P<letter>[%s])' % ''.join(WORD_MAP.keys()), re.IGNORECASE)

def iter_words(block_text):
    """
    Iterate through block text yielding Word instances
    :param block_text: text for given block with comments removed
    """
    index = 0

    while True:
        letter_match = NEXT_WORD.search(block_text[index:])
        if letter_match:
            # Letter
            letter = letter_match.group('letter').upper()
            index += letter_match.end() # propogate index to start of value

            # Value
            value_regex = WORD_MAP[letter]['value_regex']
            value_match = value_regex.search(block_text[index:])
            if value_match is None:
                raise GCodeBlockFormatError("word '%s' value invalid" % letter)
            value = value_match.group() # matched text

            yield Word(letter, value)

            index += value_match.end() # propogate index to end of value
        else:
            break

    remainder = block_text[index:]
    if remainder and re.search(r'\S', remainder):
        raise GCodeBlockFormatError("block code remaining '%s'" % remainder)


def str2word(word_str):
    words = list(iter_words(word_str))
    if words:
        assert len(words) <= 1, "more than one word given"
        return words[0]
    return None
