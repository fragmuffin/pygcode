"""
LinuxCNC

The linuxcnc gcode dialect is typically used for subtractive fabrication, such
as milling.

This dialect is the basis for all other dialects; GCodes and Words in other
dialects either inherit, or directly reference these classes.

**Specification:** http://www.linuxcnc.org

TODO: verify above info before publishing
"""

import re

from .utils import WordType

# ======================== WORDS ========================

REGEX_FLOAT = re.compile(r'^\s*-?(\d+\.?\d*|\.\d+)') # testcase: ..tests.test_words.WordValueMatchTests.test_float
REGEX_INT = re.compile(r'^\s*-?\d+')
REGEX_POSITIVEINT = re.compile(r'^\s*\d+')
REGEX_CODE = re.compile(r'^\s*\d+(\.\d)?') # float, but can't be negative

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
    'A': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of A axis (rotational axis around X axis)",
        clean_value=CLEAN_FLOAT,
    ),
    'B': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of B axis (rotational axis around Y axis)",
        clean_value=CLEAN_FLOAT,
    ),
    'C': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of C axis (rotational axis around Z axis)",
        clean_value=CLEAN_FLOAT,
    ),
    'D': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines diameter or radial offset used for cutter compensation. D is used for depth of cut on lathes. It is used for aperture selection and commands on photoplotters.",
        clean_value=CLEAN_FLOAT,
    ),
    # Feed Rates
    'E': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Precision feedrate for threading on lathes",
        clean_value=CLEAN_FLOAT,
    ),
    'F': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Feedrate",
        clean_value=CLEAN_FLOAT,
    ),
    # G-Codes
    'G': WordType(
        cls=float,
        value_regex=REGEX_CODE,
        description="Address for preparatory commands",
        clean_value=CLEAN_CODE,
    ),
    # Tool Offsets
    'H': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines tool length offset; Incremental axis corresponding to C axis (e.g., on a turn-mill)",
        clean_value=CLEAN_FLOAT,
    ),
    # Arc radius center coords
    'I': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines arc center in X axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        clean_value=CLEAN_FLOAT,
    ),
    'J': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines arc center in Y axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        clean_value=CLEAN_FLOAT,
    ),
    'K': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines arc center in Z axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles, equal to L address.",
        clean_value=CLEAN_FLOAT,
    ),
    # Loop Count
    'L': WordType(
        cls=int,
        value_regex=REGEX_POSITIVEINT,
        description="Fixed cycle loop count; Specification of what register to edit using G10",
        clean_value=CLEAN_INT,
    ),
    # Miscellaneous Function
    'M': WordType(
        cls=float,
        value_regex=REGEX_CODE,
        description="Miscellaneous function",
        clean_value=CLEAN_CODE,
    ),
    # Line Number
    'N': WordType(
        cls=int,
        value_regex=REGEX_POSITIVEINT,
        description="Line (block) number in program; System parameter number to change using G10",
        clean_value=CLEAN_INT,
    ),
    # Program Name
    'O': WordType(
        cls=str,
        value_regex=re.compile(r'^.+$'), # all the way to the end
        description="Program name",
        clean_value=CLEAN_NONE,
    ),
    # Parameter (arbitrary parameter)
    'P': WordType(
        cls=float, # parameter is often an integer, but can be a float
        value_regex=REGEX_FLOAT,
        description="Serves as parameter address for various G and M codes",
        clean_value=CLEAN_FLOAT,
    ),
    # Peck increment
    'Q': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Depth to increase on each peck; Peck increment in canned cycles",
        clean_value=CLEAN_FLOAT,
    ),
    # Arc Radius
    'R': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines size of arc radius, or defines retract height in milling canned cycles",
        clean_value=CLEAN_FLOAT,
    ),
    # Spindle speed
    'S': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Defines speed, either spindle speed or surface speed depending on mode",
        clean_value=CLEAN_FLOAT,
    ),
    # Tool Selecton
    'T': WordType(
        cls=str,
        value_regex=REGEX_POSITIVEINT, # tool string may have leading '0's, but is effectively an index (integer)
        description="Tool selection",
        clean_value=CLEAN_NONE,
    ),
    # Incremental axes
    'U': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Incremental axis corresponding to X axis (typically only lathe group A controls) Also defines dwell time on some machines (instead of 'P' or 'X').",
        clean_value=CLEAN_FLOAT,
    ),
    'V': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Incremental axis corresponding to Y axis",
        clean_value=CLEAN_FLOAT,
    ),
    'W': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Incremental axis corresponding to Z axis (typically only lathe group A controls)",
        clean_value=CLEAN_FLOAT,
    ),
    # Linear Axes
    'X': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of X axis.",
        clean_value=CLEAN_FLOAT,
    ),
    'Y': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of Y axis.",
        clean_value=CLEAN_FLOAT,
    ),
    'Z': WordType(
        cls=float,
        value_regex=REGEX_FLOAT,
        description="Absolute or incremental position of Z axis.",
        clean_value=CLEAN_FLOAT,
    ),
}


# ======================== G-CODES ========================
