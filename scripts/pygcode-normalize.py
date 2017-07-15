#!/usr/bin/env python

# Script to take (theoretically) any g-code file as input, and output a
# normalized version of it.
#
# Script outcome can have cursory verification with:
#   https://nraynaud.github.io/webgcode/

import argparse
import re
from collections import defaultdict
from contextlib import contextmanager

for pygcode_lib_type in ('installed_lib', 'relative_lib'):
    try:
        # pygcode
        from pygcode import Word
        from pygcode import Machine, Mode, Line
        from pygcode import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
        from pygcode import GCodeCannedCycle
        from pygcode import split_gcodes
        from pygcode import Comment
        from pygcode.transform import linearize_arc
        from pygcode.transform import ArcLinearizeInside, ArcLinearizeOutside, ArcLinearizeMid
        from pygcode.gcodes import _subclasses
        from pygcode.utils import omit_redundant_modes

    except ImportError:
        import sys, os, inspect
        # Add pygcode (relative to this test-path) to the system path
        _this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        sys.path.insert(0, os.path.join(_this_path, '..'))
        if pygcode_lib_type == 'installed_lib':
            continue # import was attempted before sys.path addition. retry import
        raise # otherwise the raised ImportError is a genuine problem
    break


# =================== Command Line Arguments ===================
# --- Defaults
DEFAULT_PRECISION = 0.005  # mm
DEFAULT_MACHINE_MODE = 'G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0'
DEFAULT_ARC_LIN_METHOD = 'm'
DEFAULT_CANNED_CODES = ','.join(str(w) for w in sorted(c.word_key for c in _subclasses(GCodeCannedCycle) if c.word_key))

# --- Create Parser
parser = argparse.ArgumentParser(description='Normalize gcode for machine consistency using different CAM software')
parser.add_argument(
    'infile', type=argparse.FileType('r'), nargs=1,
    help="gcode file to normalize",
)

parser.add_argument(
    '--precision', '-p', dest='precision', type=float, default=DEFAULT_PRECISION,
    help="maximum positional error when generating gcodes (eg: arcs to lines) "
         "(default: %g)" % DEFAULT_PRECISION,
)

# Machine
parser.add_argument(
    '--machine_mode', '-mm', dest='machine_mode', default=DEFAULT_MACHINE_MODE,
    help="Machine's startup mode as gcode (default: '%s')" % DEFAULT_MACHINE_MODE,
)

# Arc Linearizing
group = parser.add_argument_group(
    "Arc Linearizing",
    "Converting arcs (G2/G3 codes) into linear interpolations (G1 codes) to "
    "aproximate the original arc. Indistinguishable from an original arc when "
    "--precision is set low enough."
)
group.add_argument(
    '--arc_linearize', '-al', dest='arc_linearize',
    action='store_const', const=True, default=False,
    help="convert G2,G3 commands to a series of linear interpolations (G1 codes)",
)
group.add_argument(
    '--arc_lin_method', '-alm', dest='arc_lin_method', default=DEFAULT_ARC_LIN_METHOD,
    help="Method of linearizing arcs, i=inner, o=outer, m=mid. List 2 "
         "for <ccw>,<cw>, eg 'i,o'. 'i' is equivalent to 'i,i'. "
         "(default: '%s')" % DEFAULT_ARC_LIN_METHOD,
    metavar='{i,o,m}[,{i,o,m}]',
)

# Canned Cycles
group = parser.add_argument_group(
    "Canned Cycle Simplification",
    "Convert canned cycles into basic linear or scalar codes, such as linear "
    "interpolation (G1), and pauses (or 'dwells', G4)"
)
group.add_argument(
    '--canned_simplify', '-cs', dest='canned_simplify',
    action='store_const', const=True, default=False,
    help="Convert canned cycles into basic linear movements",
)
group.add_argument(
    '---canned_codes', '-cc', dest='canned_codes', default=DEFAULT_CANNED_CODES,
    help="List of canned gcodes to simplify, (default is '%s')" % DEFAULT_CANNED_CODES,
)

#parser.add_argument(
#    '--arc_alignment', '-aa', dest='arc_alignment', type=str, choices=('XYZ','IJK','R'),
#    default=None,
#    help="enforce precision on arcs, if XYZ the destination is altered to match the radius"
#         "if IJK or R then the arc'c centre point is moved to assure precision",
#)

# --- Parse Arguments
args = parser.parse_args()


# --- Manually Parsing : Arc Linearizing Method
# args.arc_lin_method = {Word('G2'): <linearize method class>, ... }
ARC_LIN_CLASS_MAP = {
    'i': ArcLinearizeInside,
    'o': ArcLinearizeOutside,
    'm': ArcLinearizeMid,
}

arc_lin_method_regex = re.compile(r'^(?P<g2>[iom])(,(?P<g3>[iom]))?$', re.I)
if args.arc_lin_method:
    match = arc_lin_method_regex.search(args.arc_lin_method)
    if not match:
        raise RuntimeError("parameter for --arc_lin_method is invalid: '%s'" % args.arc_lin_method)

    # changing args.arc_lin_method (because I'm a fiend)
    args.arc_lin_method = {}
    args.arc_lin_method[Word('g2')] = ARC_LIN_CLASS_MAP[match.group('g2')]
    if match.group('g3'):
        args.arc_lin_method[Word('g3')] = ARC_LIN_CLASS_MAP[match.group('g3')]
    else:
        args.arc_lin_method[Word('g3')] = args.arc_lin_method[Word('g2')]
else:
    # FIXME: change default to ArcLinearizeMid (when it's working)
    args.arc_lin_method = defaultdict(lambda: ArcLinearizeMid) # just to be sure


# --- Manually Parsing : Canned Codes
# args.canned_codes = [Word('G73'), Word('G89'), ... ]
canned_code_words = set()
for word_str in re.split(r'\s*,\s*', args.canned_codes):
    canned_code_words.add(Word(word_str))

args.canned_codes = canned_code_words


# =================== Create Virtual CNC Machine ===================
class MyMode(Mode):
    default_mode = args.machine_mode

class MyMachine(Machine):
    MODE_CLASS = MyMode

machine = MyMachine()

# =================== Utility Functions ===================
def gcodes2str(gcodes):
    return ' '.join("%s" % g for g in gcodes)


@contextmanager
def split_and_process(gcode_list, gcode_class, comment):
    """
    Split gcodes by given class, yields given class instance
    :param gcode_list: list of GCode instances
    :param gcode_class: class inheriting from GCode (directly, or indirectly)
    :param comment: Comment instance, or None
    """
    (befores, (g,), afters) = split_gcodes(gcode_list, gcode_class)
    # print & process those before gcode_class instance
    if befores:
        print(gcodes2str(befores))
        machine.process_gcodes(*befores)
    # yield, then process gcode_class instance
    yield g
    machine.process_gcodes(g)
    # print & process those after gcode_class instance
    if afters:
        print(gcodes2str(afters))
        machine.process_gcodes(*afters)
    # print comment (if given)
    if comment:
        print(str(line.comment))


# =================== Process File ===================

for line_str in args.infile[0].readlines():
    line = Line(line_str)

    # Effective G-Codes:
    #   fills in missing motion modal gcodes (using machine's current motion mode).
    effective_gcodes = machine.block_modal_gcodes(line.block)

    if args.arc_linearize and any(isinstance(g, GCodeArcMove) for g in effective_gcodes):
        with split_and_process(effective_gcodes, GCodeArcMove, line.comment) as arc:
            linearize_params = {
                'arc_gcode': arc,
                'start_pos': machine.pos,
                'plane': machine.mode.plane_selection,
                'method_class': args.arc_lin_method[arc.word],
                'dist_mode': machine.mode.distance,
                'arc_dist_mode': machine.mode.arc_ijk_distance,
                'max_error': args.precision,
                'decimal_places': 3,
            }
            for linear_gcode in omit_redundant_modes(linearize_arc(**linearize_params)):
                print(linear_gcode)

    elif args.canned_simplify and any((g.word in args.canned_codes) for g in effective_gcodes):
        (befores, (canned,), afters) = split_gcodes(effective_gcodes, GCodeCannedCycle)
        print(Comment('canning simplified: %r' % canned))

        # TODO: simplify canned things

        print(str(line))
        machine.process_block(line.block)

    else:
        print(str(line))
        machine.process_block(line.block)
