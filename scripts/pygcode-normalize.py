#!/usr/bin/env python
import argparse

for pygcode_lib_type in ('installed_lib', 'relative_lib'):
    try:
        # pygcode
        from pygcode import Machine, Mode, Line
        from pygcode import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
        from pygcode import split_gcodes
        from pygcode.transform import linearize_arc

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
    help="maximum positional error when generating gcodes (eg: arcs to lines)",
)

# Machine
parser.add_argument(
    '--machine_mode', '-mm', dest='machine_mode', default=DEFAULT_MACHINE_MODE,
    help="Machine's startup mode as gcode (default: '%s')" % DEFAULT_MACHINE_MODE,
)

# Arcs
parser.add_argument(
    '--arcs_linearize', '-al', dest='arcs_linearize',
    action='store_const', const=True, default=False,
    help="convert G2/3 commands to a series of linear G1 linear interpolations",
)
parser.add_argument(
    '--arc_alignment', '-aa', dest='arc_alignment', type=str, choices=('XYZ','IJK','R'),
    default=None,
    help="enforce precision on arcs, if XYZ the destination is altered to match the radius"
         "if IJK or R then the arc'c centre point is moved to assure precision",
)

# --- Parse Arguments
args = parser.parse_args()


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
print(args)

for line_str in args.infile[0].readlines():
    line = Line(line_str)

    effective_gcodes = machine.block_modal_gcodes(line.block)

    if any(isinstance(g, GCodeArcMove) for g in effective_gcodes):
        print("---------> Found an Arc <----------")
        (before, (arc,), after) = split_gcodes(effective_gcodes, GCodeArcMove)
        if before:
            print(gcodes2str(before))
        print(str(arc))
        if after:
            print(gcodes2str(after))



    print("%r, %s" % (sorted(line.block.gcodes), line.block.modal_params))

    machine.process_block(line.block)
