import re
from copy import copy, deepcopy
from collections import defaultdict

from .gcodes import (
    MODAL_GROUP_MAP, GCode,
    # Modal GCodes
    GCodeMotion,
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

    def __copy__(self):
        return self.__class__(axes=copy(self.axes), unit=self._unit, **self.values)

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

    # Equality
    def __eq__(self, other):
        if self.axes ^ other.axes:
            return False
        else:
            if self._unit == other._unit:
                return self._value == other._value
            else:
                x = copy(other)
                x.unit = self._unit
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
    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        if value != self._unit:
            factor = UNIT_MAP[self._unit]['conversion_factor'][value]
            for k in [k for (k, v) in self._value.items() if v is not None]:
                self._value[k] *= factor
            self._unit = value

    # Min/Max
    @classmethod
    def _cmp(cls, p1, p2, key):
        """
        Returns a position of the combined min/max values for each axis
        (eg: key=min for)
        note: the result is not necessarily equal to either p1 or p2.
        :param p1: Position instance
        :param p2: Position instance
        :return: Position instance with the highest/lowest value per axis
        """
        if p2.unit != p1.unit:
            p2 = copy(p2)
            p2.unit = p1.unit
        return cls(
            unit=p1.unit,
            **dict(
                (k, key(getattr(p1, k), getattr(p2, k))) for k in p1.values
            )
        )

    @classmethod
    def min(cls, a, b):
        return cls._cmp(a, b, key=min)

    @classmethod
    def max(cls, a, b):
        return cls._cmp(a, b, key=max)

    # Words & Values
    @property
    def words(self):
        return sorted(Word(k, self._value[k]) for k in self.axes)

    @property
    def values(self):
        return dict(self._value)

    @property
    def vector(self):
        return Vector3(self._value['X'], self._value['Y'], self._value['Z'])

    # String representation(s)
    def __repr__(self):
        return "<{class_name}: {coordinates}>".format(
            class_name=self.__class__.__name__,
            coordinates=' '.join(str(w) for w in self.words)
        )


class CoordinateSystem(object):
    def __init__(self, axes=None):
        self.offset = Position(axes=axes)

    def __copy__(self):
        obj = self.__class__()
        obj.offset = copy(self.offset)
        return obj

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
        self._axes = axes
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

    def __copy__(self):
        obj = self.__class__(axes=self._axes)
        obj.coord_systems = [copy(cs) for cs in self.coord_systems]
        obj.offset = copy(self.offset)
        return obj

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
    # Default Mode
    #   for a Grbl controller this can be obtained with the `$G` command, eg:
    #       > $G
    #       > [GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]
    #   ref: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands#g---view-gcode-parser-state
    # NOTE : there is no default mode for some machines (eg haas), so if the
    # previous program leaves the machine in G91 it will remain in G91 at the
    # beginning of the next program.. it is good practice to start programs
    # with a few "safe startup" blocks for example
    # G21       ( metric )
    # G0 G17 G40 G49 G80 G90
    # G54       ( set wcs )

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
    def __init__(self, set_default=True):
        self.modal_groups = defaultdict(lambda: None)

        # Initialize (from multiline self.default_mode)
        if set_default:
            gcodes = []
            for m in re.finditer(r'\s*(?P<line>.*)\s*\n?', self.default_mode):
                gcodes += Line(m.group('line')).block.gcodes
            self.set_mode(*gcodes)

    def __copy__(self):
        obj = self.__class__(set_default=False)
        obj.modal_groups = deepcopy(self.modal_groups)
        return obj

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
    ignore_invalid_modal = False

    def __init__(self):
        self.mode = self.MODE_CLASS()
        self.state = self.STATE_CLASS(axes=self.axes)

        # Position type (with default axes the same as this machine)
        units_mode = getattr(self.mode, 'units', None)
        self.Position = type('Position', (Position,), {
            'default_axes': self.axes,
            'default_unit': units_mode.unit_id if units_mode else Position.default_unit,
        })

        # Absolute machine position
        self.abs_pos = self.Position()
        # Machine's motion range (min/max corners of a bounding box)
        self.abs_range_min = copy(self.abs_pos)
        self.abs_range_max = copy(self.abs_pos)

    def __copy__(self):
        obj = self.__class__()
        obj.mode = copy(self.mode)
        obj.state = copy(self.state)
        obj.abs_pos = copy(self.abs_pos)
        obj.abs_range_min = copy(self.abs_range_min)
        obj.abs_range_max = copy(self.abs_range_max)
        return obj

    def set_mode(self, *gcode_list):
        self.mode.set_mode(*gcode_list)  # passthrough

        # Act on mode changes
        coord_sys_mode = self.mode.coordinate_system
        if coord_sys_mode:
            self.state.cur_coord_sys = coord_sys_mode.coord_system_id

        # TODO: convert coord systems between inches/mm, G20/G21 respectively
        # NOTE : on at least a Haas -- this cannot be changed when running a
        # program -- the G20 / G21 codes don't actually change units, but if
        # a G20 / G21 appears in the code and the machine settings do not match
        # an error will be thrown.

    def modal_gcode(self, modal_params):
        """
        :param ignore_unassigned: if truthy, unassigned parameters will be ignored
        """

        if not modal_params:
            return None

        if self.mode.motion is None:
            (modal_gcodes, unasigned_words) = ([], modal_params)
            # forces exception to be raised in next step
        else:
            params = copy(self.mode.motion.params)  # dict
            params.update(dict((w.letter, w) for w in modal_params))  # override retained modal parameters
            (modal_gcodes, unasigned_words) = words2gcodes(
                [self.mode.motion.word] + list(params.values())
            )

        if unasigned_words and (not self.ignore_invalid_modal):
            # Can't process with unknown words on the same line...
            # 2 choices:
            #   - raise MachineInvalidState
            #   - or remove unassigned parameters from line
            plausable_codes = [w for w in unasigned_words if w.letter in set('GM')]
            if plausable_codes:
                # words in list are probably valid, but unsupported, G-Codes
                # raise exception with a more helpfull message
                raise MachineInvalidState("unsupported gcode(s): '%s' (machine mode: %r)" % (
                    ' '.join(str(x) for x in unasigned_words), self.mode
                ))
            else:
                # words don't look like gcodes, assuming they're misplaced motion parameters
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

    def clean_block(self, block):
        """
        Remove invalid modal parameters from given block
        :param block: Block instance to clean
        """
        assert isinstance(block, Block), "invalid parameter"
        if self.mode.motion is None:
            # no modal motion, modal parameters are all invalid
            block.modal_params = []
        elif any(True for g in block.gcodes if g.modal_group == GCodeMotion.modal_group):
            # block defines new motion, modal motion is irrelevant
            block.modal_params = []
        else:
            (modal_gcodes, unasigned_words) = words2gcodes(
                [self.mode.motion.word] + list(block.modal_params)
            )
            for w in unasigned_words:
                block.modal_params.remove(w)

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

    # Position conversions (considering offsets)
    def abs2work(self, abs_pos):
        assert isinstance(abs_pos, Position), "bad abs_pos type"
        coord_sys_offset = getattr(self.state.coord_sys, 'offset', Position(axes=self.axes))
        temp_offset = self.state.offset
        return (abs_pos - coord_sys_offset) - temp_offset

    def work2abs(self, work_pos):
        assert isinstance(work_pos, Position), "bad work_pos type"
        coord_sys_offset = getattr(self.state.coord_sys, 'offset', Position(axes=self.axes))
        temp_offset = self.state.offset
        return (work_pos + temp_offset + coord_sys_offset)

    @property
    def pos(self):
        """Return current position in current coordinate system"""
        return self.abs2work(self.abs_pos)

    @pos.setter
    def pos(self, value):
        """Set absolute position given current position and coordinate system"""
        self.abs_pos = self.work2abs(value)
        self._update_abs_range(self.abs_pos)

    def _update_abs_range(self, pos):
        self.abs_range_min = Position.min(pos, self.abs_range_min)
        self.abs_range_max = Position.max(pos, self.abs_range_max)

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


# Null Machine
#   A machine that presumes nothing
class NullMode(Mode):
    default_mode = ''

class NullState(State):
    pass  # no change (yet)

class NullMachine(Machine):
    MODE_CLASS = NullMode
    STATE_CLASS = NullState
