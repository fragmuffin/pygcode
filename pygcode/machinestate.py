from .gcodes import GCode
from .line import Line


class State(object):
    """State of a Machine"""
    # State is very forgiving:
    #   Anything possible in a machine's state may be changed & fetched.
    #   For example: x, y, z, a, b, c may all be set & requested.
    #   However, the machine for which this state is stored probably doesn't
    #   have all possible 6 axes.
    #   It is also possible to set an axis to an impossibly large distance.
    #   It is the responsibility of the Machine using this class to be
    #   discerning in these respects.
    def __init__(self):
        self.axes = defaultdict(lambda: 0.0) # aka: "machine coordinates"

        self.work_offset = defaultdict(lambda: 0.0)
        # TODO: how to manage work offsets? (probs not like the above)
        # read up on:
        #   - G92: coordinate system offset
        #   - G54-G59: select coordinate system (offsets from machine coordinates set by G10 L2)

        # TODO: Move this class into MachineState


class MachineState(object):
    """Machine's state, and mode"""
    # Mode is defined by gcodes set by processed blocks:
    #   see modal_group in gcode.py module for details
    def __init__(self):
        self.modal_groups = defaultdict(lambda: None)
        # populate with all groups
        for modal_group in MODAL_GROUP_MAP.values():
            self.modal_groups[modal_group] = None

        # Default mode:
        self.set_mode(*Line('''
            G17       (plane_selection: X/Y plane)
            G90       (distance: absolute position. ie: not "turtle" mode)
            G91.1     (arc_ijk_distance: IJK sets arc center vertex relative to current position)
            G94       (feed_rate_mode: feed-rate defined in units/min)
            G21       (units: mm)
            G40       (cutter_diameter_comp: no compensation)
            G49       (tool_length_offset: no offset)
            G61       (control_mode: exact path mode)
            G97       (spindle_speed_mode: RPM Mode)
            M0        (stopping: program paused)
            M5        (spindle: off)
            M9        (coolant: off)
            F100      (feed_rate: 100 mm/min)
            S1000     (tool: 1000 rpm, when it's switched on)
        ''').block.gcodes) # note: although this is not a single line
                           #    '\n' is just treated like any other whitespace,
                           #    so it behaves like a single line.

    def set_mode(self, *gcode_list):
        for g in sorted(gcode_list): # sorted by execution order
            if g.modal_group is not None:
                self.modal_groups[g.modal_group] = g

    def __getattr__(self, key):
        if key in MODAL_GROUP_MAP:
            return self.modal_groups[MODAL_GROUP_MAP[key]]

        raise AttributeError("'{cls}' object has no attribute '{key}'".format(
            cls=self.__class__.__name__,
            key=key
        ))

    def __setattr__(self, key, value):
        if key in MODAL_GROUP_MAP:
            # Set/Clear modal group gcode
            if value is None:
                # clear mode group
                self.modal_groups[MODAL_GROUP_MAP[key]] = None
            else:
                # set mode group explicitly
                # (recommended to use self.set_mode(value) instead)
                assert isinstance(value, GCode), "invalid value type: %r" % value
                assert value.modal_group == MODAL_GROUP_MAP[key], \
                    "cannot set '%s' mode as %r, wrong group" % (key, value)
                self.modal_groups[MODAL_GROUP_MAP[key]] = value
        else:
            self.__dict__[key] = value

    def __str__(self):
        gcode_list = []
        for modal_group in sorted(MODAL_GROUP_MAP.values()):
            if self.modal_groups[modal_group]:
                gcode_list.append(self.modal_groups[modal_group])
        return ' '.join(str(g) for g in gcode_list)

    def __repr__(self):
        return "<{class_name}: {gcodes}>".format(
            class_name=self.__class__.__name__, gcodes=str(self)
        )
