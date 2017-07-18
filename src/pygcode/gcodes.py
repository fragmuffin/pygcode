import sys
from collections import defaultdict
from copy import copy
import six

from .utils import Vector3, Quaternion, quat2coord_system
from .words import Word, text2words

from .exceptions import GCodeParameterError, GCodeWordStrError

# Terminology of a "G-Code"
#   For the purposes of this library, so-called "G" codes do not necessarily
#   use the letter "G" in their word; other letters include M, F, S, and T
# Why?
#   I've seen documentation thrown around using the term "gcode" interchangably
#   for any word that triggers an action, or mode change. The fact that the
#   entire language is called "gcode" obfuscates any other convention.
#   Considering it's much easier for me to call everything GCode, I'm taking
#   the lazy route, so sue me (but seriously, please don't sue me).
#
# Modality groups
#   Modal GCodes:
#       A machine's "mode" can be changed by any gcode with a modal_group.
#       This state is retained by the machine in the blocks to follow until
#       the "mode" is revoked, or changed.
#       A typical example of this is units:
#           G20
#       this will change the machine's "mode" to treat all positions as
#       millimeters; G20 does not have to be on every line, thus the machine's
#       "mode" is in millimeters for that, and every block after it until G21
#       is specified (changing units to inches).
#
#   Modal Groups:
#       Only one mode of each modal group can be active. That is to say, a
#       modal g-code can only change the sate of a previously set mode if
#       they're in the same group.
#       For example:
#           G20 (mm), and G21 (inches) are in group 6
#           G1 (linear movement), and G2 (arc movement) are in group 1
#       A machine can't use mm and inches at the same time, just as it can't
#       move in a straight line, and move in an arc simultaneously.
#
#   There are 15 groups:
#       ref: http://linuxcnc.org/docs/html/gcode/overview.html#_modal_groups
#
#                 Table 5. G-Code Modal Groups
#       MODAL GROUP MEANING                     MEMBER WORDS
#       Non-modal codes (Group 0)               G4, G10 G28, G30, G53, G92, G92.1, G92.2, G92.3,
#       Motion (Group 1)                        G0, G1, G2, G3, G33, G38.x, G73, G76, G80, G81
#                                               G82, G83, G84, G85, G86, G87, G88,G89
#       Plane selection (Group 2)               G17, G18, G19, G17.1, G18.1, G19.1
#       Distance Mode (Group 3)                 G90, G91
#       Arc IJK Distance Mode (Group 4)         G90.1, G91.1
#       Feed Rate Mode (Group 5)                G93, G94, G95
#       Units (Group 6)                         G20, G21
#       Cutter Diameter Compensation (Group 7)  G40, G41, G42, G41.1, G42.1
#       Tool Length Offset (Group 8)            G43, G43.1, G49
#       Canned Cycles Return Mode (Group 10)    G98, G99
#       Coordinate System (Group 12)            G54, G55, G56, G57, G58, G59,
#                                               G59.1, G59.2, G59.3
#       Control Mode (Group 13)                 G61, G61.1, G64
#       Spindle Speed Mode (Group 14)           G96, G97
#       Lathe Diameter Mode (Group 15)          G7, G8
#
#                 Table 6. M-Code Modal Groups
#       MODAL GROUP MEANING                     MEMBER WORDS
#       Stopping (Group 4)                      M0, M1, M2, M30, M60
#       Spindle (Group 7)                       M3, M4, M5
#       Coolant (Group 8)                       (M7 M8 can both be on), M9
#       Override Switches (Group 9)             M48, M49
#       User Defined (Group 10)                 M100-M199
#

MODAL_GROUP_MAP = {
    # "G" codes
    'motion': 1,
    'plane_selection': 2,
    'distance': 3,
    'arc_ijk_distance': 4,
    'feed_rate_mode': 5,
    'units': 6,
    'cutter_diameter_comp': 7,
    'tool_length_offset': 8,
    'canned_cycles_return': 10,
    'coordinate_system': 12,
    'control_mode': 13,
    'spindle_speed_mode': 14,
    'lathe_diameter': 15,

    # "M" codes
    'stopping': 104,
    'spindle': 107,
    'coolant': 108,
    'override_switches': 109,
    'user_defined': 110,

    # Traditionally Non-grouped:
    #   Although these GCodes set the machine's mode, there are no other GCodes to
    #   group with them. So although they're modal, they doesn't have a defined
    #   modal group.
    #   However, having a modal group assists with:
    #       - validating gcode blocks for conflicting commands
    #       - remembering machine's state with consistency across gcodes
    #   Therefore, I've added F, S, and T GCodes to custom group numbers (> 200)
    'feed_rate': 201,
    'spindle_speed': 202,
    'tool': 203,
}

# Execution Order
#       Order taken http://linuxcnc.org/docs/html/gcode/overview.html#_g_code_order_of_execution
#         (as of 2017-07-03)
#       010: O-word commands (optionally followed by a comment but no other words allowed on the same line)
#       020: Comment (including message)
#       030: Set feed rate mode (G93, G94).
#       040: Set feed rate (F).
#       050: Set spindle speed (S).
#       060: Select tool (T).
#       070: HAL pin I/O (M62-M68).
#       080: Change tool (M6) and Set Tool Number (M61).
#       090: Spindle on or off (M3, M4, M5).
#       100: Save State (M70, M73), Restore State (M72), Invalidate State (M71).
#       110: Coolant on or off (M7, M8, M9).
#       120: Enable or disable overrides (M48, M49,M50,M51,M52,M53).
#       130: User-defined Commands (M100-M199).
#       140: Dwell (G4).
#       150: Set active plane (G17, G18, G19).
#       160: Set length units (G20, G21).
#       170: Cutter radius compensation on or off (G40, G41, G42)
#       180: Cutter length compensation on or off (G43, G49)
#       190: Coordinate system selection (G54, G55, G56, G57, G58, G59, G59.1, G59.2, G59.3).
#       200: Set path control mode (G61, G61.1, G64)
#       210: Set distance mode (G90, G91).
#       220: Set retract mode (G98, G99).
#       230: Go to reference location (G28, G30) or change coordinate system data (G10) or set axis offsets (G92, G92.1, G92.2, G94).
#       240: Perform motion (G0 to G3, G33, G38.x, G73, G76, G80 to G89), as modified (possibly) by G53.
#       250: Stop (M0, M1, M2, M30, M60).


class GCode(object):
    # Defining Word
    word_key = None # Word instance to use in lookup
    word_matches = None # function (secondary)
    default_word = None
    word_letter = 'G'
    word_value_configurable = False  # if set, word value can be the first parameter

    # Parameters associated to this gcode
    param_letters = set()

    # Modal stuff
    modal_group = None
    modal_param_letters = set() # by default: no parameters are retained in modal state

    # Execution Order
    exec_order = 999  # if not otherwise specified, run last

    def __init__(self, *words, **params):
        """
        :param word: Word instance defining gcode (eg: Word('G0') for rapid movement)
        :param params: list of Word instances (eg: Word('X-1.2') as x-coordinate)
        """
        gcode_word_list = words[:1]
        param_words = words[1:]
        if gcode_word_list:
            gcode_word = gcode_word_list[0]
            if self.word_value_configurable and isinstance(gcode_word, six.integer_types + (float,)):
                gcode_word = Word(self.word_letter, gcode_word)  # cast to Word()
        else:
            gcode_word = self._default_word()
        assert isinstance(gcode_word, Word), "invalid gcode word %r" % gcode_word
        self.word = gcode_word
        self.params = {}

        # Whitespace as prefix
        #   if True, str(self) will repalce self.word code with whitespace
        self._whitespace_prefix = False

        # Add Given Parameters
        for param_word in param_words:
            self.add_parameter(param_word)
        for (k, v) in params.items():
            self.add_parameter(Word(k, v))

    def __repr__(self):
        param_str = ''
        if self.params:
            param_str = "{%s}" % (', '.join([
                "{}".format(self.params[k])
                for k in sorted(self.params.keys())
            ]))
        return "<{class_name}: {gcode}{params}>".format(
            class_name=self.__class__.__name__,
            gcode=self.word,
            params=param_str,
        )

    def __str__(self):
        """String representation of gcode, as it would be seen in a .gcode file"""
        param_str = ''
        if self.params:
            param_str += ' ' + ' '.join([
                "{}".format(self.params[k])
                for k in sorted(self.params.keys())
            ])
        word_str = str(self.word)
        if self._whitespace_prefix:
            word_str = ' ' * len(word_str)
        return "{word_str}{parameters}".format(
            word_str=word_str,
            parameters=param_str,
        )

    def _default_word(self):
        if self.default_word:
            return copy(self.default_word)
        elif self.word_key:
            return copy(self.word_key)
        raise AssertionError("class %r has no default word" % self.__class__)

    # Comparisons
    def __lt__(self, other):
        """Sort by execution order"""
        return self.exec_order < other.exec_order

    def __gt__(self, other):
        """Sort by execution order"""
        return self.exec_order > other.exec_order

    # Parameters
    def add_parameter(self, word):
        """
        Add given word as a parameter for this gcode
        :param word: Word instance
        """
        assert isinstance(word, Word), "invalid parameter class: %r" % word
        if word.letter not in self.param_letters:
            raise GCodeParameterError("invalid parameter for %s: %s" % (self.__class__.__name__, str(word)))
        if word.letter in self.params:
            raise GCodeParameterError("parameter defined twice: %s -> %s" % (self.params[word.letter], word))

        self.params[word.letter] = word

    # Assert Parameters
    def assert_params(self):
        """
        Assert validity of gcode's parameters.
        This verification is irrespective of machine, or machine's state;
        verification is g-code language-based verification
        :raises: GCodeParameterError
        """
        # to be overridden in inheriting classes
        pass

    def __getattr__(self, key):
        # Return parameter values (if valid parameter for gcode)
        if key in self.param_letters:
            if key in self.params:
                return self.params[key].value
            else:
                return None # parameter is valid for GCode, but undefined

        raise AttributeError("'{cls}' object has no attribute '{key}'".format(
            cls=self.__class__.__name__,
            key=key
        ))

    def __setattr__(self, key, value):
        if key in self.param_letters:
            if key in self.params:
                self.params[key].value = value
            else:
                self.add_parameter(Word(key, value))

        else:
            self.__dict__[key] = value

    @property
    def description(self):
        return self.__doc__

    def modal_copy(self):
        """Copy of GCode instance containing only parameters listed in modal_param_letters"""
        return self.__class__(self.word, *[
            w for (l, w) in self.params.items()
            if l in self.modal_param_letters
        ])

    def get_param_dict(self, letters=None, lc=False):
        """
        Get gcode parameters as a dict
        gcode parameter like "X3.1, Y-2" would return {'X': 3.1, 'Y': -2}
        :param letters: iterable whitelist of letters to include as dict keys
        :param lc: lower case parameter letters
        :return: dict of gcode parameters' (letter, value) pairs
        """
        letter_mod = lambda x: x
        if lc:
            letter_mod = lambda x: x.lower()
        return dict(
            (letter_mod(w.letter), w.value) for w in self.params.values()
            if (letters is None) or (w.letter in letters)
        )

    # Process GCode
    def process(self, machine):
        """
        Process a GCode on the given Machine
        :param machine: Machine instance, to change state
        :return: GCodeEffect instance; effect the gcode just had on machine
        """
        from .machine import Machine  # importing up (done live to avoid dependency loop)
        assert isinstance(machine, Machine), "invalid machine type: %r" % machine

        # Set mode
        self._process_mode(machine)

        # GCode specific
        self._process(machine)

    def _process_mode(self, machine):
        """Set machine's state"""
        machine.set_mode(self)

    def _process(self, machine):
        """Process this GCode (to be overridden)"""
        pass



# ======================= Motion =======================
#   (X Y Z A B C U V W apply to all motions)
# CODE          PARAMETERS      DESCRIPTION
# G0                            Rapid Move
# G1                            Linear Move
# G2, G3        I J K or R, P   Arc Move
# G4            P               Dwell
# G5            I J P Q         Cubic Spline
# G5.1          I J             Quadratic Spline
# G5.2          P L             NURBS
# G38.2 - G38.5                 Straight Probe
# G33           K               Spindle Synchronized Motion
# G33.1         K               Rigid Tapping
# G80                           Cancel Canned Cycle

class GCodeMotion(GCode):
    param_letters = set('XYZABCUVW')
    modal_group = MODAL_GROUP_MAP['motion']
    exec_order = 241

    def _process(self, machine):
        machine.move_to(**self.get_param_dict(letters=machine.axes))


class GCodeRapidMove(GCodeMotion):
    """G0: Rapid Move"""
    word_key = Word('G', 0)

    def _process(self, machine):
        machine.move_to(rapid=True, **self.get_param_dict(letters=machine.axes))


class GCodeLinearMove(GCodeMotion):
    """G1: Linear Move"""
    word_key = Word('G', 1)


class GCodeArcMove(GCodeMotion):
    """Arc Move"""
    param_letters = GCodeMotion.param_letters | set('IJKRP')

    def assert_params(self):
        param_letters = set(self.params.keys())
        # Parameter groups
        params_xyz = set('XYZ') & set(param_letters)
        params_ijk = set('IJK') & set(param_letters)
        params_r = set('R') & set(param_letters)
        params_ijkr = params_ijk | params_r

        # --- Parameter Groups
        # XYZ: at least 1
        if not params_xyz:
            raise GCodeParameterError("no XYZ parameters set for destination: %r" % arc_gcode)
        # IJK or R: only in 1 group
        if params_ijk and params_r:
            raise GCodeParameterError("both IJK and R parameters defined: %r" % arc_gcode)
        # IJKR: at least 1
        if not params_ijkr:
            raise GCodeParameterError("neither IJK or R parameters defined: %r" % arc_gcode)

        # --- Parameter Values
        if params_r and (self.R == 0):
            raise GCodeParameterError("cannot plot a circle with a radius of zero: %r" % arc_gcode)


class GCodeArcMoveCW(GCodeArcMove):
    """G2: Arc Move (clockwise)"""
    word_key = Word('G', 2)


class GCodeArcMoveCCW(GCodeArcMove):
    """G3: Arc Move (counter-clockwise)"""
    word_key = Word('G', 3)


class GCodeDwell(GCodeMotion):
    """G4: Dwell"""
    param_letters = set('P')  # doesn't accept axis parameters
    word_key = Word('G', 4)
    modal_group = None  # one of the few motion commands that isn't modal
    exec_order = 140

    def _process(self, machine):
        pass  # no movements made


class GCodeCublcSpline(GCodeMotion):
    """G5: Cubic Spline"""
    param_letters = GCodeMotion.param_letters | set('IJPQ')
    word_key = Word('G', 5)


class GCodeQuadraticSpline(GCodeMotion):
    """G5.1: Quadratic Spline"""
    param_letters = GCodeMotion.param_letters | set('IJ')
    word_key = Word('G', 5.1)


class GCodeNURBS(GCodeMotion):
    """G5.2: Non-uniform rational basis spline (NURBS)"""
    param_letters = GCodeMotion.param_letters | set('PL')
    word_key = Word('G', 5.2)


class GCodeNURBSEnd(GCodeNURBS):
    """G5.3: end NURBS mode"""
    word_key = Word('G', 5.3)


class GCodeStraightProbe(GCodeMotion):
    """G38.2-G38.5: Straight Probe"""
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (38.2 <= w.value <= 38.5)
    default_word = Word('G', 38.2)


class GCodeSpindleSyncMotion(GCodeMotion):
    """G33: Spindle Synchronized Motion"""
    param_letters = GCodeMotion.param_letters | set('K')
    word_key = Word('G', 33)


class GCodeRigidTapping(GCodeMotion):
    """G33.1: Rigid Tapping"""
    param_letters = GCodeMotion.param_letters | set('K')
    word_key = Word('G', 33.1)


class GCodeCancelCannedCycle(GCodeMotion):
    """G80: Cancel Canned Cycle"""
    word_key = Word('G', 80)


# ======================= Canned Cycles =======================
#      (X Y Z or U V W apply to canned cycles, depending on active plane)
# CODE              PARAMETERS          DESCRIPTION
# G81               R L (P)             Drilling Cycle
# G82               R L (P)             Drilling Cycle, Dwell
# G83               R L Q               Drilling Cycle, Peck
# G73               R L Q               Drilling Cycle, Chip Breaking
# G85               R L (P)             Boring Cycle, Feed Out
# G89               R L (P)             Boring Cycle, Dwell, Feed Out
# G76               P Z I J R K Q H L E Threading Cycle

class GCodeCannedCycle(GCode):
    param_letters = set('XYZUVW')
    modal_group = MODAL_GROUP_MAP['motion']
    exec_order = 241

    def _process(self, machine):
        moveto_coords = self.get_param_dict(letters=machine.axes)
        if isinstance(machine.mode.canned_cycles_return, GCodeCannedCycleReturnToR):
            # canned return is to this.R, not this.Z (plane dependent)
            moveto_coords.update({
                machine.mode.plane_selection.normal_axis: this.R,
            })

        machine.move_to(**moveto_coords)


class GCodeDrillingCycle(GCodeCannedCycle):
    """G81: Drilling Cycle"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 81)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RP')


class GCodeDrillingCycleDwell(GCodeCannedCycle):
    """G82: Drilling Cycle, Dwell"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 82)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RP')


class GCodeDrillingCyclePeck(GCodeCannedCycle):
    """G83: Drilling Cycle, Peck"""
    param_letters = GCodeCannedCycle.param_letters | set('RLQ')
    word_key = Word('G', 83)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RQ')


class GCodeDrillingCycleChipBreaking(GCodeCannedCycle):
    """G73: Drilling Cycle, ChipBreaking"""
    param_letters = GCodeCannedCycle.param_letters | set('RLQ')
    word_key = Word('G', 73)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RQ')


class GCodeBoringCycleFeedOut(GCodeCannedCycle):
    """G85: Boring Cycle, Feed Out"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 85)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RP')


class GCodeBoringCycleDwellFeedOut(GCodeCannedCycle):
    """G89: Boring Cycle, Dwell, Feed Out"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 89)
    modal_param_letters = GCodeCannedCycle.param_letters | set('RP')


class GCodeThreadingCycle(GCodeCannedCycle):
    """G76: Threading Cycle"""
    param_letters = GCodeCannedCycle.param_letters | set('PZIJRKQHLE')
    word_key = Word('G', 76)


# ======================= Distance Mode =======================
# CODE              PARAMETERS          DESCRIPTION
# G90, G91                              Distance Mode
# G90.1, G91.1                          Arc Distance Mode
# G7                                    Lathe Diameter Mode
# G8                                    Lathe Radius Mode

class GCodeDistanceMode(GCode):
    exec_order = 210


class GCodeAbsoluteDistanceMode(GCodeDistanceMode):
    """G90: Absolute Distance Mode"""
    word_key = Word('G', 90)
    modal_group = MODAL_GROUP_MAP['distance']


class GCodeIncrementalDistanceMode(GCodeDistanceMode):
    """G91: Incremental Distance Mode"""
    word_key = Word('G', 91)
    modal_group = MODAL_GROUP_MAP['distance']


class GCodeAbsoluteArcDistanceMode(GCodeDistanceMode):
    """G90.1: Absolute Distance Mode for Arc IJK Parameters"""
    word_key = Word('G', 90.1)
    modal_group = MODAL_GROUP_MAP['arc_ijk_distance']


class GCodeIncrementalArcDistanceMode(GCodeDistanceMode):
    """G91.1: Incremental Distance Mode for Arc IJK Parameters"""
    word_key = Word('G', 91.1)
    modal_group = MODAL_GROUP_MAP['arc_ijk_distance']


class GCodeLatheDiameterMode(GCodeDistanceMode):
    """G7: Lathe Diameter Mode"""
    word_key = Word('G', 7)
    modal_group = MODAL_GROUP_MAP['lathe_diameter']


class GCodeLatheRadiusMode(GCodeDistanceMode):
    """G8: Lathe Radius Mode"""
    word_key = Word('G', 8)
    modal_group = MODAL_GROUP_MAP['lathe_diameter']


# ======================= Feed Rate Mode =======================
# CODE              PARAMETERS          DESCRIPTION
# G93, G94, G95                         Feed Rate Mode

class GCodeFeedRateMode(GCode):
    modal_group = MODAL_GROUP_MAP['feed_rate_mode']
    exec_order = 30


class GCodeInverseTimeMode(GCodeFeedRateMode):
    """G93: Inverse Time Mode"""
    word_key = Word('G', 93)


class GCodeUnitsPerMinuteMode(GCodeFeedRateMode):
    """G94: Units Per MinuteMode"""
    word_key = Word('G', 94)


class GCodeUnitsPerRevolution(GCodeFeedRateMode):
    """G95: Units Per Revolution"""
    word_key = Word('G', 95)


# ======================= Spindle Control =======================
# CODE              PARAMETERS          DESCRIPTION
# M3, M4, M5        S                   Spindle Control
# M19                                   Orient Spindle
# G96, G97          S D                 Spindle Control Mode

class GCodeSpindle(GCode):
    word_letter = 'M'
    exec_order = 90


class GCodeStartSpindle(GCodeSpindle):
    """M3,M4: Start Spindle Clockwise"""
    modal_group = MODAL_GROUP_MAP['spindle']


class GCodeStartSpindleCW(GCodeStartSpindle):
    """M3: Start Spindle Clockwise"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 3)

class GCodeStartSpindleCCW(GCodeStartSpindle):
    """M4: Start Spindle Counter-Clockwise"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 4)


class GCodeStopSpindle(GCodeSpindle):
    """M5: Stop Spindle"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 5)
    modal_group = MODAL_GROUP_MAP['spindle']


class GCodeOrientSpindle(GCodeSpindle):
    """M19: Orient Spindle"""
    word_key = Word('M', 19)


class GCodeSpindleSpeedMode(GCodeSpindle):
    word_letter = 'G'
    modal_group = MODAL_GROUP_MAP['spindle_speed_mode']


class GCodeSpindleConstantSurfaceSpeedMode(GCodeSpindleSpeedMode):
    """G96: Spindle Constant Surface Speed"""
    param_letters = set('DS')
    word_key = Word('G', 96)


class GCodeSpindleRPMMode(GCodeSpindleSpeedMode):
    """G97: Spindle RPM Speed"""
    param_letters = set('D')
    word_key = Word('G', 97)



# ======================= Coolant =======================
# CODE              PARAMETERS          DESCRIPTION
# M7, M8, M9                            Coolant Control

class GCodeCoolant(GCode):
    word_letter = 'M'
    modal_group = MODAL_GROUP_MAP['coolant']
    exec_order = 110


class GCodeCoolantMistOn(GCodeCoolant):
    """M7: turn mist coolant on"""
    word_key = Word('M', 7)


class GCodeCoolantFloodOn(GCodeCoolant):
    """M8: turn flood coolant on"""
    word_key = Word('M', 8)


class GCodeCoolantOff(GCodeCoolant):
    """M9: turn all coolant off"""
    word_key = Word('M', 9)


# ======================= Tool Length =======================
# CODE              PARAMETERS          DESCRIPTION
# G43               H                   Tool Length Offset
# G43.1                                 Dynamic Tool Length Offset
# G43.2             H                   Apply additional Tool Length Offset
# G49                                   Cancel Tool Length Compensation

class GCodeToolLength(GCode):
    modal_group = MODAL_GROUP_MAP['tool_length_offset']
    exec_order = 180


class GCodeToolLengthOffset(GCodeToolLength):
    """G43: Tool Length Offset"""
    param_letters = set('H')
    word_key = Word('G', 43)


class GCodeDynamicToolLengthOffset(GCodeToolLength):
    """G43.1: Dynamic Tool Length Offset"""
    word_key = Word('G', 43.1)


class GCodeAddToolLengthOffset(GCodeToolLength):
    """G43.2: Appkly Additional Tool Length Offset"""
    param_letters = set('H')
    word_key = Word('G', 43.2)


class GCodeCancelToolLengthOffset(GCodeToolLength):
    """G49: Cancel Tool Length Compensation"""
    word_key = Word('G', 49)


# ======================= Stopping (Program Control) =======================
# CODE              PARAMETERS          DESCRIPTION
# M0, M1                                Program Pause
# M2, M30                               Program End
# M60                                   Pallet Change Pause

class GCodeProgramControl(GCode):
    word_letter = 'M'
    modal_group = MODAL_GROUP_MAP['stopping']
    exec_order = 250

class GCodePauseProgram(GCodeProgramControl):
    """M0: Program Pause"""
    word_key = Word('M', 0)


class GCodePauseProgramOptional(GCodeProgramControl):
    """M1: Program Pause (optional)"""
    word_key = Word('M', 1)


class GCodeEndProgram(GCodeProgramControl):
    """M2: Program End"""
    word_key = Word('M', 2)


class GCodeEndProgramPalletShuttle(GCodeProgramControl):
    """M30: exchange pallet shuttles and end the program"""
    word_key = Word('M', 30)


class GCodePalletChangePause(GCodeProgramControl):
    """M60: Pallet Change Pause"""
    word_key = Word('M', 60)


# ======================= Units =======================
# CODE              PARAMETERS          DESCRIPTION
# G20, G21                              Units

class GCodeUnit(GCode):
    modal_group = MODAL_GROUP_MAP['units']
    exec_order = 160


class GCodeUseInches(GCodeUnit):
    """G20: use inches for length units"""
    word_key = Word('G', 20)
    unit_id = 0


class GCodeUseMillimeters(GCodeUnit):
    """G21: use millimeters for length units"""
    word_key = Word('G', 21)
    unit_id = 1


# ======================= Plane Selection =======================
#       (affects G2, G3, G81-G89, G40-G42)
# CODE              PARAMETERS          DESCRIPTION
# G17 - G19.1                           Plane Select

class GCodePlaneSelect(GCode):
    modal_group = MODAL_GROUP_MAP['plane_selection']
    exec_order = 150

    # -- Plane Orientation Quaternion
    # Such that...
    #   vectorXY = Vector3(<your coords in X/Y plane>)
    #   vectorZX = GCodeSelectZXPlane.quat * vectorXY
    #   vectorZX += some_offset_vector
    #   vectorXY = GCodeSelectZXPlane.quat.conjugate() * vectorZX
    # note: all quaternions use the XY plane as a basis
    # To transform from ZX to YZ planes via these quaternions, you must
    # first translate it to XY, like so:
    #   vectorYZ = GCodeSelectYZPlane.quat * (GCodeSelectZXPlane.quat.conjugate() * vectorZX)
    quat = None  # Quaternion

    # -- Plane Normal
    # Vector normal to plane (such that XYZ axes follow the right-hand rule)
    normal_axis = None  # Letter of normal axis (upper case)
    normal = None  # Vector3


class GCodeSelectXYPlane(GCodePlaneSelect):
    """G17: select XY plane (default)"""
    word_key = Word('G', 17)
    quat = Quaternion()  # no effect
    normal_axis = 'Z'
    normal = Vector3(0., 0., 1.)


class GCodeSelectZXPlane(GCodePlaneSelect):
    """G18: select ZX plane"""
    word_key = Word('G', 18)
    quat = quat2coord_system(
        Vector3(1., 0., 0.), Vector3(0., 1., 0.),
        Vector3(0., 0., 1.), Vector3(1., 0., 0.)
    )
    normal_axis = 'Y'
    normal = Vector3(0., 1., 0.)


class GCodeSelectYZPlane(GCodePlaneSelect):
    """G19: select YZ plane"""
    word_key = Word('G', 19)
    quat = quat2coord_system(
        Vector3(1., 0., 0.), Vector3(0., 1., 0.),
        Vector3(0., 1., 0.), Vector3(0., 0., 1.)
    )
    normal_axis = 'X'
    normal = Vector3(1., 0., 0.)


class GCodeSelectUVPlane(GCodePlaneSelect):
    """G17.1: select UV plane"""
    word_key = Word('G', 17.1)


class GCodeSelectWUPlane(GCodePlaneSelect):
    """G18.1: select WU plane"""
    word_key = Word('G', 18.1)


class GCodeSelectVWPlane(GCodePlaneSelect):
    """G19.1: select VW plane"""
    word_key = Word('G', 19.1)


# ======================= Cutter Radius Compensation =======================
# CODE              PARAMETERS          DESCRIPTION
# G40                                   Compensation Off
# G41,G42           D                   Cutter Compensation
# G41.1, G42.1      D L                 Dynamic Cutter Compensation

class GCodeCutterRadiusComp(GCode):
    modal_group = MODAL_GROUP_MAP['cutter_diameter_comp']
    exec_order = 170


class GCodeCutterRadiusCompOff(GCodeCutterRadiusComp):
    """G40: Cutter Radius Compensation Off"""
    word_key = Word('G', 40)


class GCodeCutterCompLeft(GCodeCutterRadiusComp):
    """G41: Cutter Radius Compensation (left)"""
    param_letters = set('D')
    word_key = Word('G', 41)


class GCodeCutterCompRight(GCodeCutterRadiusComp):
    """G42: Cutter Radius Compensation (right)"""
    param_letters = set('D')
    word_key = Word('G', 42)


class GCodeDynamicCutterCompLeft(GCodeCutterRadiusComp):
    """G41.1: Dynamic Cutter Radius Compensation (left)"""
    param_letters = set('DL')
    word_key = Word('G', 41.1)


class GCodeDynamicCutterCompRight(GCodeCutterRadiusComp):
    """G42.1: Dynamic Cutter Radius Compensation (right)"""
    param_letters = set('DL')
    word_key = Word('G', 42.1)


# ======================= Path Control Mode =======================
# CODE              PARAMETERS          DESCRIPTION
# G61 G61.1                             Exact Path Mode
# G64               P Q                 Path Blending

class GCodePathControlMode(GCode):
    modal_group = MODAL_GROUP_MAP['control_mode']
    exec_order = 200


class GCodeExactPathMode(GCodePathControlMode):
    """G61: Exact path mode"""
    word_key = Word('G', 61)


class GCodeExactStopMode(GCodePathControlMode):
    """G61.1: Exact stop mode"""
    word_key = Word('G', 61.1)


class GCodePathBlendingMode(GCodePathControlMode):
    """G64: Path Blending"""
    param_letters = set('PQ')
    word_key = Word('G', 64)


# ======================= Return Mode in Canned Cycles =======================
# CODE              PARAMETERS          DESCRIPTION
# G98                                   Canned Cycle Return Level to previous
# G99                                   Canned Cycle Return to the level set by R

class GCodeCannedReturnMode(GCode):
    modal_group = MODAL_GROUP_MAP['canned_cycles_return']
    exec_order = 220


class GCodeCannedCycleReturnLevel(GCodeCannedReturnMode):
    """G98: Canned Cycle Return to the level set prior to cycle start"""
    # "retract to the position that axis was in just before this series of one or more contiguous canned cycles was started"
    word_key = Word('G', 98)


class GCodeCannedCycleReturnToR(GCodeCannedReturnMode):
    """G99: Canned Cycle Return to the level set by R"""
    # "retract to the position specified by the R word of the canned cycle"
    word_key = Word('G', 99)


# ======================= Other Modal Codes =======================
# CODE              PARAMETERS          DESCRIPTION
# F                                     Set Feed Rate
# S                                     Set Spindle Speed
# T                                     Select Tool
# M48, M49                              Speed and Feed Override Control
# M50               P0 (off) or P1 (on) Feed Override Control
# M51               P0 (off) or P1 (on) Spindle Speed Override Control
# M52               P0 (off) or P1 (on) Adaptive Feed Control
# M53               P0 (off) or P1 (on) Feed Stop Control
# G54-G59.3                             Select Coordinate System

class GCodeOtherModal(GCode):
    pass


class GCodeFeedRate(GCodeOtherModal):
    """F: Set Feed Rate"""
    word_letter = 'F'
    word_value_configurable = True
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'F'
    default_word = Word('F', 0)
    modal_group = MODAL_GROUP_MAP['feed_rate']
    exec_order = 40


class GCodeSpindleSpeed(GCodeOtherModal):
    """S: Set Spindle Speed"""
    word_letter = 'S'
    word_value_configurable = True
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'S'
    default_word = Word('S', 0)
    # Modal Group: (see description in GCodeFeedRate)
    modal_group = MODAL_GROUP_MAP['spindle_speed']
    exec_order = 50


class GCodeSelectTool(GCodeOtherModal):
    """T: Select Tool"""
    word_letter = 'T'
    word_value_configurable = True
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'T'
    default_word = Word('T', 0)
    # Modal Group: (see description in GCodeFeedRate)
    modal_group = MODAL_GROUP_MAP['tool']
    exec_order = 60


class GCodeSpeedAndFeedOverrideOn(GCodeOtherModal):
    """M48: Speed and Feed Override Control On"""
    word_letter = 'M'
    word_key = Word('M', 48)
    modal_group = MODAL_GROUP_MAP['override_switches']
    exec_order = 120


class GCodeSpeedAndFeedOverrideOff(GCodeOtherModal):
    """M49: Speed and Feed Override Control Off"""
    word_letter = 'M'
    word_key = Word('M', 49)
    modal_group = MODAL_GROUP_MAP['override_switches']
    exec_order = 120


class GCodeFeedOverride(GCodeOtherModal):
    """M50: Feed Override Control"""
    word_letter = 'M'
    param_letters = set('P')
    word_key = Word('M', 50)
    exec_order = 120


class GCodeSpindleSpeedOverride(GCodeOtherModal):
    """M51: Spindle Speed Override Control"""
    word_letter = 'M'
    param_letters = set('P')
    word_key = Word('M', 51)
    exec_order = 120


class GCodeAdaptiveFeed(GCodeOtherModal):
    """M52: Adaptive Feed Control"""
    word_letter = 'M'
    param_letters = set('P')
    word_key = Word('M', 52)
    exec_order = 120


class GCodeFeedStop(GCodeOtherModal):
    """M53: Feed Stop Control"""
    word_letter = 'M'
    param_letters = set('P')
    word_key = Word('M', 53)
    exec_order = 120


class GCodeSelectCoordinateSystem(GCodeOtherModal):
    """Select Coordinate System"""
    modal_group = MODAL_GROUP_MAP['coordinate_system']
    exec_order = 190
    coord_system_id = None  # overridden in inheriting classes


class GCodeSelectCoordinateSystem1(GCodeSelectCoordinateSystem):
    """Select Coordinate System 1"""
    word_key = Word('G', 54)
    coord_system_id = 1


class GCodeSelectCoordinateSystem2(GCodeSelectCoordinateSystem):
    """Select Coordinate System 2"""
    word_key = Word('G', 55)
    coord_system_id = 2


class GCodeSelectCoordinateSystem3(GCodeSelectCoordinateSystem):
    """Select Coordinate System 3"""
    word_key = Word('G', 56)
    coord_system_id = 3


class GCodeSelectCoordinateSystem4(GCodeSelectCoordinateSystem):
    """Select Coordinate System 4"""
    word_key = Word('G', 57)
    coord_system_id = 4


class GCodeSelectCoordinateSystem5(GCodeSelectCoordinateSystem):
    """Select Coordinate System 5"""
    word_key = Word('G', 58)
    coord_system_id = 5


class GCodeSelectCoordinateSystem6(GCodeSelectCoordinateSystem):
    """Select Coordinate System 6"""
    word_key = Word('G', 59)
    coord_system_id = 6


class GCodeSelectCoordinateSystem7(GCodeSelectCoordinateSystem):
    """Select Coordinate System 7"""
    coord_system_id = 7
    word_key = Word('G', 59.1)


class GCodeSelectCoordinateSystem8(GCodeSelectCoordinateSystem):
    """Select Coordinate System 8"""
    word_key = Word('G', 59.2)
    coord_system_id = 8


class GCodeSelectCoordinateSystem9(GCodeSelectCoordinateSystem):
    """Select Coordinate System 9"""
    word_key = Word('G', 59.3)
    coord_system_id = 9


# ======================= Flow-control Codes =======================
# CODE              PARAMETERS          DESCRIPTION
# o sub                                 Subroutines, sub/endsub call        [unsupported]
# o while                               Looping, while/endwhile do/while    [unsupported]
# o if                                  Conditional, if/else/endif          [unsupported]
# o repeat                              Repeat a loop of code               [unsupported]
# []                                    Indirection                         [unsupported]
# o call                                Call named file                     [unsupported]
# M70                                   Save modal state                    [unsupported]
# M71                                   Invalidate stored state             [unsupported]
# M72                                   Restore modal state                 [unsupported]
# M73                                   Save and Auto-restore modal state   [unsupported]


# ======================= Input/Output Codes =======================
# CODE              PARAMETERS          DESCRIPTION
# M62 - M65         P                   Digital Output Control
# M66               P E L Q             Wait on Input
# M67               T                   Analog Output, Synchronized
# M68               T                   Analog Output, Immediate

class GCodeIO(GCode):
    word_letter = 'M'
    exec_order = 70


class GCodeDigitalOutput(GCodeIO):
    """Digital Output Control"""
    param_letters = set('P')


class GCodeDigitalOutputOnSyncd(GCodeDigitalOutput):
    """M62: turn on digital output synchronized with motion"""
    word_key = Word('M', 62)


class GCodeDigitalOutputOffSyncd(GCodeDigitalOutput):
    """M63: turn off digital output synchronized with motion"""
    word_key = Word('M', 63)


class GCodeDigitalOutputOn(GCodeDigitalOutput):
    """M64: turn on digital output immediately"""
    word_key = Word('M', 64)


class GCodeDigitalOutputOff(GCodeDigitalOutput):
    """M65: turn off digital output immediately"""
    word_key = Word('M', 65)


class GCodeWaitOnInput(GCodeIO):
    """M66: Wait on Input"""
    param_letters = set('PELQ')
    word_key = Word('M', 66)


class GCodeAnalogOutput(GCodeIO):
    """Analog Output"""
    param_letters = set('T')


class GCodeAnalogOutputSyncd(GCodeAnalogOutput):
    """M67: Analog Output, Synchronized"""
    word_key = Word('M', 67)


class GCodeAnalogOutputImmediate(GCodeAnalogOutput):
    """M68: Analog Output, Immediate"""
    word_key = Word('M', 68)


# ======================= Non-modal Codes =======================
# CODE              PARAMETERS          DESCRIPTION
# M6                T                   Tool Change
# M61               Q                   Set Current Tool
# G10 L1            P Q R               Set Tool Table
# G10 L10           P                   Set Tool Table
# G10 L11           P                   Set Tool Table
# G10 L2            P R                 Set Coordinate System
# G10 L20           P                   Set Coordinate System
# G28, G28.1                            Go/Set Predefined Position
# G30, G30.1                            Go/Set Predefined Position
# G53                                   Move in Machine Coordinates
# G92                                   Coordinate System Offset
# G92.1, G92.2                          Reset G92 Offsets
# G92.3                                 Restore G92 Offsets
# M101 - M199       P Q                 User Defined Commands

class GCodeNonModal(GCode):
    pass


class GCodeToolChange(GCodeNonModal):
    """M6: Tool Change"""
    param_letters = set('T')
    word_key = Word('M', 6)
    word_letter = 'M'
    exec_order = 80


class GCodeToolSetCurrent(GCodeNonModal):
    """M61: Set Current Tool"""
    param_letters = set('Q')
    word_key = Word('M', 61)
    word_letter = 'M'
    exec_order = 80


class GCodeSet(GCodeNonModal):
    """G10: Set stuff"""
    param_letters = set('LPQR')
    word_key = Word('G', 10)
    exec_order = 230


class GCodeGotoPredefinedPosition(GCodeNonModal):
    """G28,G30: Goto Predefined Position (rapid movement)"""
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [28, 30])
    default_word = Word('G', 28)
    exec_order = 230


class GCodeSetPredefinedPosition(GCodeNonModal):
    """G28.1,G30.1: Set Predefined Position"""  # redundancy in language there, but I'll let it slide
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [28.1, 30.1])
    default_word = Word('G', 28.1)
    exec_order = 230


class GCodeMoveInMachineCoords(GCodeNonModal):
    """G53: Move in Machine Coordinates"""
    word_key = Word('G', 53)
    exec_order = 240


class GCodeCoordSystemOffset(GCodeNonModal):
    """G92: Coordinate System Offset"""
    word_key = Word('G', 92)
    exec_order = 230


class GCodeResetCoordSystemOffset(GCodeNonModal):
    """G92.1,G92.2: Reset Coordinate System Offset"""
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [92.1, 92.2])
    default_word = Word('G', 92.1)
    exec_order = 230

    # TODO: machine.state.offset *= 0


class GCodeRestoreCoordSystemOffset(GCodeNonModal):
    """G92.3: Restore Coordinate System Offset"""
    word_key = Word('G', 92.3)
    exec_order = 230


class GCodeUserDefined(GCodeNonModal):
    """M101-M199: User Defined Commands"""
    word_letter = 'M'
    # To create user g-codes, inherit from this class
    param_letters = set('PQ')
    #@classmethod
    #def word_matches(cls, w):
    #    return (w.letter == 'M') and (101 <= w.value <= 199)
    #default_word = Word('M', 101)
    exec_order = 130
    modal_group = MODAL_GROUP_MAP['user_defined']


# ======================= Utilities =======================

def _subclasses_level(root_class, recursion_level=0):
    """
    Hierarcical list of all classes inheriting from the given root class (recursive)
    :param root_class: class used as trunk of hierarchy (included inoutput)
    :param recursion_level: should always be 0 (unless recursively called)
    :param
    """
    yield (root_class, recursion_level)
    for cls in sorted(root_class.__subclasses__(), key=lambda c: c.__name__):
        for (sub, level) in _subclasses_level(cls, recursion_level+1):
            yield (sub, level)


def _subclasses(root_class):
    """Flat list of all classes inheriting from the given root class (recursive)"""
    for (cls, level) in _subclasses_level(root_class):
        yield cls


def _gcode_class_infostr(base_class=GCode, prefix=''):
    """
    List all ineheriting classes for the given gcode class
    :param base_class: root of hierarcy
    :return: str listing all gcode classes
    """
    info_str = ""
    for (cls, level) in _subclasses_level(base_class):
        word_str = ''
        if cls.word_key:
            word_str = str(cls.word_key)
        info_str += "{prefix}{word} {indent}- {name}: {description}\n".format(
            prefix=prefix,
            word="%-5s" % word_str,
            indent=(level * "  "),
            name=cls.__name__,
            description=cls.__doc__ or "",
        )
    return info_str


# ======================= GCode Word Mapping =======================
_gcode_maps_created = False  # only set when the below values are populated
_gcode_word_map = {} # of the form: {Word('G', 0): GCodeRapidMove, ... }
_gcode_function_list = [] # of the form: [(lambda w: w.letter == 'F', GCodeFeedRate), ... ]


def build_maps():
    """Populate _gcode_word_map and _gcode_function_list"""
    # Ensure Word maps / lists are clear
    global _gcode_word_map
    global _gcode_function_list
    _gcode_word_map = {}
    _gcode_function_list = []

    for cls in _subclasses(GCode):
        if cls.word_key is not None:
            # Map Word instance to g-code class
            if cls.word_key in _gcode_word_map:
                raise RuntimeError("Multiple GCode classes map to '%s'" % str(cls.word_key))
            _gcode_word_map[cls.word_key] = cls
        elif cls.word_matches is not None:
            # Add to list of functions
            _gcode_function_list.append((cls.word_matches, cls))

    global _gcode_maps_created
    _gcode_maps_created = True


# ======================= Words -> GCodes =======================
def word_gcode_class(word, exhaustive=False):
    """
    Map word to corresponding GCode class
    :param word: Word instance
    :param exhausitve: if True, all words are tested; not just 'GMFST'
    :return: class inheriting GCode
    """

    if not _gcode_maps_created:
        build_maps()

    # quickly eliminate parameters
    if (not exhaustive) and (word.letter not in 'GMFST'):
        return None

    # by Word Map (faster)
    if word in _gcode_word_map:
        return _gcode_word_map[word]

    # by Function List (slower, so checked last)
    for (match_function, gcode_class) in _gcode_function_list:
        if match_function(word):
            return gcode_class

    return None


def words2gcodes(words):
    """
    Group words into g-codes (includes both G & M codes)
    :param words: list of Word instances
    :return: tuple([<GCode>, <GCode>, ...], list(<unused words>))
    """

    gcodes = []
    # Lines to consider
    # Conflicts with non G|M codes (ie: S|F|T)
    #   Spindle Control:
    #       - S1000
    #       - M3 S2000
    #   Tool Change:
    #       - T2
    #       - M6 T1
    #
    # Conclusion: words are parameters first, gcodes second

    # First determine which words are GCode candidates
    word_info_list = [
        {
            'index': i, # for internal referencing
            'word': word,
            'gcode_class': word_gcode_class(word), # if not None, word is a candidate
            'param_to_index': None,
        }
        for (i, word) in enumerate(words)
    ]

    # Link parameters to candidates
    # note: gcode candidates may be valid parameters... therefore
    # Also eliminate candidates that are parameters for earlier gcode candidates
    for word_info in word_info_list:
        if word_info['gcode_class'] is None:
            continue # not a gcode candidate, so cannot have parameters
        # which of the words following this gcode candidate are a valid parameter
        for param_info in word_info_list[word_info['index'] + 1:]:
            if param_info['word'].letter in word_info['gcode_class'].param_letters:
                param_info['param_to_index'] = word_info['index']
                param_info['gcode_class'] = None # no longer a valid candidate

    # Map parameters
    parameter_map = defaultdict(list) # {<gcode word index>: [<parameter words>], ... }
    for word_info in word_info_list:
        if word_info['gcode_class']:
            continue # will form a gcode, so must not also be a parameter
        parameter_map[word_info['param_to_index']].append(word_info['word'])

    # Create gcode instances
    for word_info in word_info_list:
        if word_info['gcode_class'] is None:
            continue # not a gcode candidate
        gcode = word_info['gcode_class'](
            word_info['word'],
            *parameter_map[word_info['index']] # gcode parameters
        )
        gcodes.append(gcode)

    return (gcodes, parameter_map[None])


def text2gcodes(text):
    """
    Convert text to GCode instances (must be fully formed; no modal parameters)
    :param text: line from a g-code file
    :return: tuple([<GCode>, <GCode>, ...], list(<unused words>))
    """
    words = list(text2words(text))
    (gcodes, modal_words) = words2gcodes(words)
    if modal_words:
        raise GCodeWordStrError("gcode text not fully formed, unassigned parameters: %r" % modal_words)
    return gcodes


# ======================= Utilities =======================

def split_gcodes(gcode_list, splitter_class, sort_list=True):
    """
    Splits a list of GCode instances into 3, the center list containing the splitter_class gcode
    :param gcode_list: list of GCode instances to split
    :param splitter_class: class of gcode identifying split from left to right
    :return: list of: [[<gcodes before splitter>], [<splitter instance>], [<gcodes after splitter>]]
    """
    # for example:
    #     g_list = sorted([g1, g2, g3, g4])
    #     split_gcodes(g_list, type(g2)) == [[g1], [g2], [g3, g4]]
    # 3 lists are always returned, even if empty; if 2nd list is empty,
    # then the 3rd will be as well.
    if sort_list: # sort by execution order first
        gcode_list = sorted(gcode_list)

    split = [gcode_list, [], []]  # default (if no splitter can be found)

    # Find splitter index (only one can be found)
    split_index = None
    for (i, gcode) in enumerate(gcode_list):
        if isinstance(gcode, splitter_class):
            split_index = i
            break

    # Form split: pivoting around split_index
    if split_index is not None:
        split[0] = gcode_list[:split_index]
        split[1] = [gcode_list[split_index]]
        split[2] = gcode_list[split_index+1:]

    return split


def _gcodes_abs2rel(start_pos, dist_mode=None, axes='XYZ'):
    """
    Decorator to convert returned motion gcode coordinates to incremental.
    Intended to be used internally (mainly because it's a little shonky).
    Function being decorated is only expected to return GCodeRapidMove or
    GCodeLinearMove instances.
    :param start_pos: starting machine position (Position)
    :param dist_mode: machine's distance mode (GCodeAbsoluteDistanceMode or GCodeIncrementalDistanceMode)
    :param axes: axes machine accepts (set)
    """
    # Usage:
    #   m = Machine()  # defaults to absolute distance mode
    #   m.process_gcodes(GCodeRapidMove(X=10, Y=20, Z=3))
    #   m.process_gcodes(GCodeIncrementalDistanceMode())
    #
    #   @_gcodes_abs2rel(start_pos=m.pos, dist_mode=m.mode.distance, axes=m.axes)
    #   def do_stuff():
    #       yield GCodeRapidMove(X=0, Y=30, Z=3)
    #       yield GCodeLinearMove(X=0, Y=30, Z=-5)
    #
    #   gcode_list = do_stuff()
    #   gocde_list[0] # == GCodeRapidMove(X=-10, Y=10)
    #   gocde_list[1] # == GCodeLinearMove(Z=-8)

    SUPPORTED_MOTIONS = (
        GCodeRapidMove, GCodeLinearMove,
    )

    def wrapper(func):

        def inner(*largs, **kwargs):
            # Create Machine (with minimal information)
            from .machine import Machine, Mode, Position
            m = type('AbsoluteCoordMachine', (Machine,), {
                'MODE_CLASS': type('NullMode', (Mode,), {'default_mode': 'G90'}),
                'axes': axes,
            })()
            m.pos = start_pos

            for gcode in func(*largs, **kwargs):
                # Verification & passthrough's
                if not isinstance(gcode, GCode):
                    yield gcode  # whatever this thing is
                else:
                    # Process gcode
                    pos_from = m.pos
                    m.process_gcodes(gcode)
                    pos_to = m.pos

                    if gcode.modal_group != MODAL_GROUP_MAP['motion']:
                        yield gcode  # only deal with motion gcodes
                        continue
                    elif not isinstance(gcode, SUPPORTED_MOTIONS):
                        raise NotImplementedError("%r to iterative coords is not supported (this is only a very simple function)" % gcode)

                    # Convert coordinates to iterative
                    rel_pos = pos_to - pos_from
                    coord_words = [w for w in rel_pos.words if w.value]
                    if coord_words:  # else relative coords are all zero; do nothing
                        yield words2gcodes([gcode.word] + coord_words)[0].pop()


        # Return apropriate function
        if (dist_mode is None) or isinstance(dist_mode, GCodeIncrementalDistanceMode):
            return inner
        else:
            return func  # bypass decorator entirely; nothing to be done
    return wrapper
