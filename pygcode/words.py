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


ORDER_LINUXCNC_LETTER_MAP = {
    'O': 10,
    'F': 40,
    'S': 50,
    'T': 60,
}

_v_csv = lambda v, ks: [(k, v) for k in ks.split(',')]

ORDER_LINUXCNC_LETTERVALUE_MAP = dict(itertools.chain.from_iterable([
    _v_csv(30, 'G93,G94'),
    _v_csv(70, 'M62,M63,M64,M65,M66,M67,M68'),
    _v_csv(80, 'M6,M61'),
    _v_csv(90, 'M3,M4,M5'),
    _v_csv(100, 'M71,M73,M72,M71'),
    _v_csv(110, 'M7,M8,M9'),
    _v_csv(120, 'M48,M49,M50,M51,M52,M53'),
    [('G4', 140)],
    _v_csv(150, 'G17,G18,G19'),
    _v_csv(160, 'G20,G21'),
    _v_csv(170, 'G40,G41,G42'),
    _v_csv(180, 'G43,G49'),
    _v_csv(190, 'G54,G55,G56,G57,G58,G59,G59.1,G59.2,G59.3'),
    _v_csv(200, 'G61,G61.1,G64'),
    _v_csv(210, 'G90,G91'),
    _v_csv(220, 'G98,G99'),
    _v_csv(230, 'G28,G30,G10,G92,G92.1,G92.2,G94'),
    _v_csv(240, 'G0,G1,G2,G3,G33,G73,G76,G80,G81,G82,G83,G84,G85,G86,G87,G88,G89'),
    _v_csv(250, 'M0,M1,M2,M30,M60'),
]))

def _word_order_linuxcnc(word):
    '''
    Order taken http://linuxcnc.org/docs/html/gcode/overview.html#_g_code_order_of_execution
        (as of 2017-07-03)
    010: O-word commands (optionally followed by a comment but no other words allowed on the same line)
    N/A: Comment (including message)
    030: Set feed rate mode (G93, G94).
    040: Set feed rate (F).
    050: Set spindle speed (S).
    060: Select tool (T).
    070: HAL pin I/O (M62-M68).
    080: Change tool (M6) and Set Tool Number (M61).
    090: Spindle on or off (M3, M4, M5).
    100: Save State (M70, M73), Restore State (M72), Invalidate State (M71).
    110: Coolant on or off (M7, M8, M9).
    120: Enable or disable overrides (M48, M49,M50,M51,M52,M53).
    130: User-defined Commands (M100-M199).
    140: Dwell (G4).
    150: Set active plane (G17, G18, G19).
    160: Set length units (G20, G21).
    170: Cutter radius compensation on or off (G40, G41, G42)
    180: Cutter length compensation on or off (G43, G49)
    190: Coordinate system selection (G54, G55, G56, G57, G58, G59, G59.1, G59.2, G59.3).
    200: Set path control mode (G61, G61.1, G64)
    210: Set distance mode (G90, G91).
    220: Set retract mode (G98, G99).
    230: Go to reference location (G28, G30) or change coordinate system data (G10) or set axis offsets (G92, G92.1, G92.2, G94).
    240: Perform motion (G0 to G3, G33, G38.x, G73, G76, G80 to G89), as modified (possibly) by G53.
    250: Stop (M0, M1, M2, M30, M60).
    900 + letter val: (else)
    '''
    if word.letter in ORDER_LINUXCNC_LETTER_MAP:
        return ORDER_LINUXCNC_LETTER_MAP[word.letter]
    letter_value = str(word)
    if letter_value in ORDER_LINUXCNC_LETTERVALUE_MAP:
        return ORDER_LINUXCNC_LETTERVALUE_MAP[letter_value]

    # special cases
    if (word.letter == 'M') and (100 <= int(word.value) <= 199):
        return 130
    if (word.letter == 'G') and (38 < float(word.value) < 39):
        return 240

    # otherwise, sort last, in alphabetic order
    return (900 + (ord(word.letter) - ord('A')))

def by_linuxcnc_order(word):
    return word.orderval_linuxcnc


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
        return WORD_MAP[self.letter]['description']

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
