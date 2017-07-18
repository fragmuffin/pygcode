from copy import copy, deepcopy
from collections import defaultdict

from .gcodes import (
    MODAL_GROUP_MAP, GCode,
    # Modal GCodes
    GCodeIncrementalDistanceMode,
    GCodeUseInches, GCodeUseMillimeters,
    # Utilities
    words2gcodes,
)
from .block import Block
from .line import Line
from .words import Word
from .utils import Vector3, Quaternion

from .exceptions import MachineInvalidAxis, MachineInvalidState

UNIT_IMPERIAL = GCodeUseInches.unit_id      # G20
UNIT_METRIC = GCodeUseMillimeters.unit_id   # G21
UNIT_MAP = {
    UNIT_IMPERIAL: {
        'name': 'inches',
        'conversion_factor': { UNIT_METRIC: 25.4 },
    },
    UNIT_METRIC: {
        'name': 'millimeters',
        'conversion_factor': { UNIT_IMPERIAL: 1. / 25.4 },
    },
}


class Position(object):
    default_axes = 'XYZABCUVW'
    default_unit = UNIT_METRIC
    POSSIBLE_AXES = set('XYZABCUVW')

    def __init__(self, axes=None, **kwargs):
        # Set axes (note: usage in __getattr__ and __setattr__)
        if axes is None:
            axes = self.__class__.default_axes
        else:
            invalid_axes = set(axes) - self.POSSIBLE_AXES
            if invalid_axes:
                raise MachineInvalidAxis("invalid axes proposed %s" % invalid_axes)
        self.__dict__['axes'] = set(axes) & self.POSSIBLE_AXES

        # Unit
        self._unit = kwargs.pop('unit', self.default_unit)

        # Initial Values
        self._value = defaultdict(lambda: 0.0, dict((k, 0.0) for k in self.axes))
        self._value.update(kwargs)

    def update(self, **coords):
        for (k, v) in coords.items():
            setattr(self, k, v)

    # Attributes Get/Set
    def __getattr__(self, key):
        if key in self.axes:
            return self._value[key]

        raise AttributeError("'{cls}' object has no attribute '{key}'".format(
            cls=self.__class__.__name__,
            key=key
        ))

    def __setattr__(self, key, value):
        if key in self.axes:
            self._value[key] = value
        elif key in self.POSSIBLE_AXES:
            raise MachineInvalidAxis("'%s' axis is not defined to be set" % key)
        else:
            self.__dict__[key] = value

    # Copy
    def __copy__(self):
        return self.__class__(axes=copy(self.axes), unit=self._unit, **self.values)

    # Equality
    def __eq__(self, other):
        if self.axes ^ other.axes:
            return False
        else:
            if self._unit == other._unit:
                return self._value == other._value
            else:
                x = copy(other)
                x.set_unit(self._unit)
                return self._value == x._value

    def __ne__(self, other):
        return not self.__eq__(other)

    # Arithmetic
    def __add__(self, other):
        if self.axes ^ other.axes:
            raise MachineInvalidAxis("axes: %r != %r" % (self.axes, other.axes))
        new_obj = copy(self)
        for k in new_obj._value:
            new_obj._value[k] += other._value[k]
        return new_obj

    def __sub__(self, other):
        if other.axes - self.axes:
            raise MachineInvalidAxis("for a - b: axes in b, that are not in a: %r" % (other.axes - self.axes))
        new_obj = copy(self)
        for k in other._value:
            new_obj._value[k] -= other._value[k]
        return new_obj

    def __mul__(self, scalar):
        new_obj = copy(self)
        for k in self._value:
            new_obj._value[k] = self._value[k] * scalar
        return new_obj

    def __div__(self, scalar):
        new_obj = copy(self)
        for k in self._value:
            new_obj._value[k] = self._value[k] / scalar
        return new_obj

    __truediv__ = __div__ # Python 3 division

    # Conversion
    def set_unit(self, unit):
        if unit == self._unit:
            return
        factor = UNIT_MAP[self._unit]['conversion_factor'][unit]
        for k in [k for (k, v) in self._value.items() if v is not None]:
            self._value[k] *= factor
        self._unit = unit

    @property
    def words(self):
        return sorted(Word(k, self._value[k]) for k in self.axes)

    @property
    def values(self):
        return dict(self._value)

    @property
    def vector(self):
        return Vector3(self._value['X'], self._value['Y'], self._value['Z'])

    def __repr__(self):
        return "<{class_name}: {coordinates}>".format(
            class_name=self.__class__.__name__,
            coordinates=' '.join(str(w) for w in self.words)
        )


class CoordinateSystem(object):
    def __init__(self, axes):
        self.offset = Position(axes)

    def __add__(self, other):
        if isinstance(other, CoordinateSystem):
            pass

    def __repr__(self):
        return "<{class_name}: offset={offset}>".format(
            class_name=self.__class__.__name__,
            offset=repr(self.offset),
        )


class State(object):
    """State of a Machine"""
    # LinuxCNC documentation lists parameters for a machine's state:
    #   http://linuxcnc.org/docs/html/gcode/overview.html#sub:numbered-parameters
    # AFAIK: this is everything needed to remember a machine's state that isn't
    #        handled by modal gcodes.
    def __init__(self, axes=None):
        # Coordinate Systems
        self.coord_systems = {}
        for i in range(1, 10): # G54-G59.3
            self.coord_systems[i] = CoordinateSystem(axes)

        self.cur_coord_sys = 1 # default to coord system 1 (G54)

        # Temporary Offset
        self.offset = Position(axes) # G92 offset (reset by G92.x)

        # Missing from state (according to LinuxCNC's state variables):
        #   - G38.2 probe result (Position())
        #   - G38 probe result (bool)
        #   - M66: result (bool)
        #   - Tool offsets (Position())
        #   - Tool info (number, diameter, front angle, back angle, orientation)

        #self.work_offset = defaultdict(lambda: 0.0)

        # TODO: how to manage work offsets? (probs not like the above)
        # read up on:
        # Coordinate System config:
        #   - G92: set machine coordinate system value (no movement, effects all coordinate systems)
        #   - G10 L2: offsets the origin of the axes in the coordinate system specified to the value of the axis word
        #   - G10 L20: makes the current machine coordinates the coordinate system's offset
        # Coordinate System selection:
        #   - G54-G59: select coordinate system (offsets from machine coordinates set by G10 L2)

        # TODO: Move this class into MachineState

    @property
    def coord_sys(self):
        """Current equivalent coordinate system, including all """
        if self.cur_coord_sys in self.coord_systems:
            return self.coord_systems[self.cur_coord_sys]
        return None

    def __repr__(self):
        return "<{class_name}: coord_sys[{coord_index}]; offset={offset}>".format(
            class_name=self.__class__.__name__,
            coord_index=self.cur_coord_sys,
            offset=repr(self.offset),
        )


class Mode(object):
    """Machine's mode"""
    # State is very forgiving:
    #   Anything possible in a machine's state may be changed & fetched.
    #   For example: x, y, z, a, b, c may all be set & requested.
    #   However, the machine for which this state is stored probably doesn't
    #   have all possible 6 axes.
    #   It is also possible to set an axis to an impossibly large distance.
    #   It is the responsibility of the Machine using this class to be
    #   discerning in these respects.

    # Default Mode
    #   for a Grbl controller this can be obtained with the `$G` command, eg:
    #       > $G
    #       > [GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]
    #   ref: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands#g---view-gcode-parser-state
    default_mode = '''
        G0      (movement: rapid)
        G17     (plane_selection: X/Y plane)
        G90     (distance: absolute position. ie: not "turtle" mode)
        G91.1   (arc_ijk_distance: IJK sets arc center vertex relative to current position)
        G94     (feed_rate_mode: feed-rate defined in units/min)
        G21     (units: mm)
        G40     (cutter_diameter_comp: no compensation)
        G49     (tool_length_offset: no offset)
        G54     (coordinate_system: 1)
        G61     (control_mode: exact path mode)
        G97     (spindle_speed_mode: RPM Mode)
        M5      (spindle: off)
        M9      (coolant: off)
        F0      (feed_rate: 0)
        S0      (spindle_speed: 0)
        T0      (tool: 0)
    '''

    # Mode is defined by gcodes set by processed blocks:
    #   see modal_group in gcode.py module for details
    def __init__(self):
        self.modal_groups = defaultdict(lambda: None)

        # Initialize
        self.set_mode(*Line(self.default_mode).block.gcodes)

    def set_mode(self, *gcode_list):
        """
        Set machine mode from given gcodes (will not be processed)
        :param gcode_list: list of GCode instances (given as individual parameters)
        :return: dict of form: {<modal group>: <new mode GCode>, ...}
        """
        modal_gcodes = {}
        for g in sorted(gcode_list): # sorted by execution order
            if g.modal_group is not None:
                self.modal_groups[g.modal_group] = g.modal_copy()
                modal_gcodes[g.modal_group] = self.modal_groups[g.modal_group]
                # assumption: no 2 gcodes are in the same modal_group
        return modal_gcodes

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
                # set mode group explicitly, not advisable
                # (recommended to use self.set_mode(value) instead)
                if not isinstance(value, GCode):
                    raise MachineInvalidState("invalid mode value: %r" % value)
                if value.modal_group != MODAL_GROUP_MAP[key]:
                    raise MachineInvalidState("cannot set '%s' mode as %r, wrong group" % (key, value))
                self.modal_groups[MODAL_GROUP_MAP[key]] = value.modal_copy()
        else:
            self.__dict__[key] = value

    @property
    def gcodes(self):
        """List of modal gcodes"""
        gcode_list = []
        for modal_group in sorted(MODAL_GROUP_MAP.values()):
            if self.modal_groups[modal_group]:
                gcode_list.append(self.modal_groups[modal_group])
        return gcode_list

    def __str__(self):
        return ' '.join(str(g) for g in self.gcodes)

    def __repr__(self):
        return "<{class_name}: {gcodes}>".format(
            class_name=self.__class__.__name__, gcodes=str(self)
        )


class Machine(object):
    """Machine to process gcodes, enforce axis limits, keep track of time, etc"""

    # Class types
    MODE_CLASS = Mode
    STATE_CLASS = State

    axes = set('XYZ')

    def __init__(self):
        self.mode = self.MODE_CLASS()
        self.state = self.STATE_CLASS(axes=self.axes)

        # Position type (with default axes the same as this machine)
        units_mode = getattr(self.mode, 'units', None)
        self.Position = type('Position', (Position,), {
            'default_axes': self.axes,
            'default_unit': units_mode.unit_id if units_mode else UNIT_METRIC,
        })

        # Absolute machine position
        self.abs_pos = self.Position()

    def set_mode(self, *gcode_list):
        self.mode.set_mode(*gcode_list)  # passthrough

        # Act on mode changes
        coord_sys_mode = self.mode.coordinate_system
        if coord_sys_mode:
            self.state.cur_coord_sys = coord_sys_mode.coord_system_id

    def modal_gcode(self, modal_params):

        if not modal_params:
            return None
        if self.mode.motion is None:
            raise MachineInvalidState("unable to assign modal parameters when no motion mode is set")
        params = copy(self.mode.motion.params)  # dict
        params.update(dict((w.letter, w) for w in modal_params))  # override retained modal parameters
        (modal_gcodes, unasigned_words) = words2gcodes([self.mode.motion.word] + params.values())
        if unasigned_words:
            raise MachineInvalidState("modal parameters '%s' cannot be assigned when in mode: %r" % (
                ' '.join(str(x) for x in unasigned_words), self.mode
            ))
        if modal_gcodes:
            assert len(modal_gcodes) == 1, "more than 1 modal code found"
            return modal_gcodes[0]
        return None

    def block_modal_gcodes(self, block):
        """
        Block's GCode list in current machine mode
        :param block: Block instance
        :return: list of gcodes, block.gcodes + <modal gcode, if there is one>
        """
        assert isinstance(block, Block), "invalid parameter"
        gcodes = copy(block.gcodes)
        modal_gcode = self.modal_gcode(block.modal_params)
        if modal_gcode:
            gcodes.append(modal_gcode)
        return sorted(gcodes)

    def process_gcodes(self, *gcode_list, **kwargs):
        """
        Process gcodes
        :param gcode_list: list of GCode instances
        :param modal_params: list of Word instances to be applied to current movement mode
        """
        gcode_list = list(gcode_list) # make appendable
        # Add modal gcode to list of given gcodes
        modal_params = kwargs.get('modal_params', [])
        if modal_params:
            modal_gcode = self.modal_gcode(modal_params)
            if modal_gcode:
                gcode_list.append(modal_gcode)

        for gcode in sorted(gcode_list):
            gcode.process(self) # shifts ownership of what happens now to GCode class

            # TODO: gcode instance to change machine's state
            # Questions to drive design:
            #   - how much time did the command take?
            #   - what was the tool's distance / displacement
            #   - did the tool travel outside machine boundaries?
            # Use-cases
            #   - Transform / rotate coordinate system in given gcode
            #   - Convert arcs to linear segments (visa versa?)
            #   - Correct precision errors
            #   - Crop a file (eg: resume half way through)

    def process_block(self, block):
        self.process_gcodes(*block.gcodes, modal_params=block.modal_params)

    def process_str(self, block_str):
        line = Line(block_str)
        self.process_block(line.block)

    @property
    def pos(self):
        """Return current position in current coordinate system"""
        coord_sys_offset = getattr(self.state.coord_sys, 'offset', Position(axes=self.axes))
        temp_offset = self.state.offset
        return (self.abs_pos - coord_sys_offset) - temp_offset

    @pos.setter
    def pos(self, value):
        """Set absolute position given current position and coordinate system"""
        coord_sys_offset = getattr(self.state.coord_sys, 'offset', Position(axes=self.axes))
        temp_offset = self.state.offset
        self.abs_pos = (value + temp_offset) + coord_sys_offset

    # =================== Machine Actions ===================
    def move_to(self, rapid=False, **coords):
        """Move machine to given position"""
        if isinstance(self.mode.distance, GCodeIncrementalDistanceMode):
            pos_delta = Position(axes=self.axes, **coords)
            self.pos += pos_delta
        else:  # assumed: GCodeAbsoluteDistanceMode
            new_pos = self.pos
            new_pos.update(**coords)  # only change given coordinates
            self.pos = new_pos
