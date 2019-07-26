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

REGEX_NUMBER = re.compile(r'^\s*-?(\d+\.?\d*|\.\d+)') # testcase: ..tests.test_words.WordValueMatchTests.test_float
REGEX_POSITIVEINT = re.compile(r'^\s*\d+')
REGEX_CODE = re.compile(r'^\s*\d+(\.\d)?') # float, but can't be negative

def CLASS_NUMBER(value):
    if isinstance(value, (int, float)):
        return value
    if '.' in value:
        return float(value)
    return int(value)

# Value cleaning functions
CLEAN_NONE = lambda v: v

def CLEAN_NUMBER(v):
    if isinstance(v, int):
        return str(v)
    fstr = "{0:g}".format(round(v, 3))
    if '.' not in fstr:
        return fstr + '.'
    return fstr
CLEAN_CODE = lambda v: '{:02}'.format(v)
CLEAN_INT = lambda v: "%g" % v

WORD_MAP = {
    # Descriptions copied from wikipedia:
    #   https://en.wikipedia.org/wiki/G-code#Letter_addresses

    # Rotational Axes
    'A': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of A axis (rotational axis around X axis)",
        clean_value=CLEAN_NUMBER,
    ),
    'B': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of B axis (rotational axis around Y axis)",
        clean_value=CLEAN_NUMBER,
    ),
    'C': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of C axis (rotational axis around Z axis)",
        clean_value=CLEAN_NUMBER,
    ),
    'D': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines diameter or radial offset used for cutter compensation. D is used for depth of cut on lathes. It is used for aperture selection and commands on photoplotters.",
        clean_value=CLEAN_NUMBER,
    ),
    # Feed Rates
    'E': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Precision feedrate for threading on lathes",
        clean_value=CLEAN_NUMBER,
    ),
    'F': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Feedrate",
        clean_value=CLEAN_NUMBER,
    ),
    # G-Codes
    'G': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_CODE,
        description="Address for preparatory commands",
        clean_value=CLEAN_NONE,
    ),
    # Tool Offsets
    'H': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines tool length offset; Incremental axis corresponding to C axis (e.g., on a turn-mill)",
        clean_value=CLEAN_NUMBER,
    ),
    # Arc radius center coords
    'I': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines arc center in X axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        clean_value=CLEAN_NUMBER,
    ),
    'J': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines arc center in Y axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles.",
        clean_value=CLEAN_NUMBER,
    ),
    'K': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines arc center in Z axis for G02 or G03 arc commands. Also used as a parameter within some fixed cycles, equal to L address.",
        clean_value=CLEAN_NUMBER,
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
        cls=CLASS_NUMBER,
        value_regex=REGEX_CODE,
        description="Miscellaneous function",
        clean_value=CLEAN_NONE,
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
        cls=CLASS_NUMBER, # parameter is often an integer, but can be a float
        value_regex=REGEX_NUMBER,
        description="Serves as parameter address for various G and M codes",
        clean_value=CLEAN_NUMBER,
    ),
    # Peck increment
    'Q': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Depth to increase on each peck; Peck increment in canned cycles",
        clean_value=CLEAN_NUMBER,
    ),
    # Arc Radius
    'R': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines size of arc radius, or defines retract height in milling canned cycles",
        clean_value=CLEAN_NUMBER,
    ),
    # Spindle speed
    'S': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Defines speed, either spindle speed or surface speed depending on mode",
        clean_value=CLEAN_NUMBER,
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
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Incremental axis corresponding to X axis (typically only lathe group A controls) Also defines dwell time on some machines (instead of 'P' or 'X').",
        clean_value=CLEAN_NUMBER,
    ),
    'V': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Incremental axis corresponding to Y axis",
        clean_value=CLEAN_NUMBER,
    ),
    'W': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Incremental axis corresponding to Z axis (typically only lathe group A controls)",
        clean_value=CLEAN_NUMBER,
    ),
    # Linear Axes
    'X': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of X axis.",
        clean_value=CLEAN_NUMBER,
    ),
    'Y': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of Y axis.",
        clean_value=CLEAN_NUMBER,
    ),
    'Z': WordType(
        cls=CLASS_NUMBER,
        value_regex=REGEX_NUMBER,
        description="Absolute or incremental position of Z axis.",
        clean_value=CLEAN_NUMBER,
    ),
}


# ======================== G-CODES ========================
