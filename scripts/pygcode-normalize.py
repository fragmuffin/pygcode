#!/usr/bin/env python

# Script to take (theoretically) any g-code file as input, and output a
# normalized version of it.
#
# Script outcome can have cursory verification with:
#   https://nraynaud.github.io/webgcode/

import argparse
import re
from collections import defaultdict

for pygcode_lib_type in ('installed_lib', 'relative_lib'):
    try:
        # pygcode
        from pygcode import Machine, Mode, Line
        from pygcode import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
        from pygcode import split_gcodes
        from pygcode.transform import linearize_arc
        from pygcode.transform import ArcLinearizeInside, ArcLinearizeOutside, ArcLinearizeMid

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

# Arcs
parser.add_argument(
    '--arc_linearize', '-al', dest='arc_linearize',
    action='store_const', const=True, default=False,
    help="convert G2/3 commands to a series of linear G1 linear interpolations",
)

parser.add_argument(
    '--arc_lin_method', '-alm', dest='arc_lin_method', default='i',
    help="Method of linearizing arcs, i=inner, o=outer, m=middle. List 2 "
         "for <ccw>,<cw>, eg 'i,o'. also: 'm' is equivalent to 'm,m' ",
    metavar='{i,o,m}[,{i,o,m]',
)

parser.add_argument(
    '--arc_alignment', '-aa', dest='arc_alignment', type=str, choices=('XYZ','IJK','R'),
    default=None,
    help="enforce precision on arcs, if XYZ the destination is altered to match the radius"
         "if IJK or R then the arc'c centre point is moved to assure precision",
)

# --- Parse Arguments
args = parser.parse_args()


# arc linearizing method (manually parsing)
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
    args.arc_lin_method['G2'] = ARC_LIN_CLASS_MAP[match.group('g2')]
    if match.group('g3'):
        args.arc_lin_method['G3'] = ARC_LIN_CLASS_MAP[match.group('g3')]
    else:
        args.arc_lin_method['G3'] = args.arc_lin_method['G2']
else:
    args.arc_lin_method = defaultdict(lambda: ArcLinearizeInside) # just to be sure



# =================== Create Virtual CNC Machine ===================
class MyMode(Mode):
    default_mode = args.machine_mode

class MyMachine(Machine):
    MODE_CLASS = MyMode

machine = MyMachine()

# =================== Utility Functions ===================
def gcodes2str(gcodes):
    return ' '.join("%s" % g for g in gcodes)


# =================== Process File ===================

for line_str in args.infile[0].readlines():
    line = Line(line_str)
    #if line.comment:
    #    print("===== %s" % line.comment.text)

    effective_gcodes = machine.block_modal_gcodes(line.block)

    if args.arc_linearize and any(isinstance(g, GCodeArcMove) for g in effective_gcodes):
        #print("---------> Found an Arc <----------")
        (befores, (arc,), afters) = split_gcodes(effective_gcodes, GCodeArcMove)
        # TODO: debug printing (for now)
        if befores:
            print(gcodes2str(befores))
            machine.process_gcodes(*befores)
        #print("arc: %s" % str(arc))
        linearize_params = {
            'arc_gcode': arc,
            'start_pos': machine.pos,
            'plane': machine.mode.plane_selection,
            'method_class': args.arc_lin_method["%s%i" % (arc.word.letter, arc.word.value)],
            'dist_mode': machine.mode.distance,
            'arc_dist_mode': machine.mode.arc_ijk_distance,
            'max_error': args.precision,
            'decimal_places': 3,
        }
        for linear_gcode in linearize_arc(**linearize_params):
            print(linear_gcode)
        machine.process_gcodes(arc)

        if afters:
            print(gcodes2str(afters))
            machine.process_gcodes(*afters)
        if line.comment:
            print(str(line.comment))
    else:
        print(str(line))
        machine.process_block(line.block)



    #print("%r, %s" % (sorted(line.block.gcodes), line.block.modal_params))
