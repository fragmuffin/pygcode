from collections import defaultdict
from copy import copy

from .words import Word

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

    # Parameters associated to this gcode
    param_letters = set()

    # Modal stuff
    modal_group = None
    modal_param_letters = set() # by default: no parameters are retained in modal state

    # Execution Order
    exec_order = 999  # if not otherwise specified, run last

    def __init__(self, word, *params):
        """
        :param word: Word instance defining gcode (eg: Word('G0') for rapid movement)
        :param params: list of Word instances (eg: Word('X-1.2') as x-coordinate)
        """
        assert isinstance(word, Word), "invalid gcode word %r" % code_word
        self.word = word
        self.params = {}

        # Add Given Parameters
        for param in params:
            self.add_parameter(param)

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
                "{}".format(self.params[k].clean_str)
                for k in sorted(self.params.keys())
            ])
        return "{gcode}{parameters}".format(
            gcode=self.word.clean_str,
            parameters=param_str,
        )

    # Sort by exec_order
    def __lt__(self, other):
        return self.exec_order < other.exec_order

    def add_parameter(self, word):
        """
        Add given word as a parameter for this gcode
        :param word: Word instance
        """
        assert isinstance(word, Word), "invalid parameter class: %r" % word
        assert word.letter in self.param_letters, "invalid parameter for %s: %s" % (self.__class__.__name__, str(word))
        assert word.letter not in self.params, "parameter defined twice: %s -> %s" % (self.params[word.letter], word)
        self.params[word.letter] = word

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

    @property
    def description(self):
        return self.__doc__

    def modal_copy(self):
        """Copy of GCode instance containing only parameters listed in modal_param_letters"""
        return self.__class__(self.word, *[
            w for (l, w) in self.params.items()
            if l in self.modal_param_letters
        ])

    def get_param_dict(self, letters=None):
        """
        Get gcode parameters as a dict
        gcode parameter like "X3.1, Y-2" would return {'X': 3.1, 'Y': -2}
        :param letters: iterable whitelist of letters to include as dict keys
        :return: dict of gcode parameters' (letter, value) pairs
        """
        return dict(
            (w.letter, w.value) for w in self.params.values()
            if (letters is None) or (w.letter in letters)
        )

    # Process GCode
    def process(self, machine):
        """
        Process a GCode on the given Machine
        :param machine: Machine instance, to change state
        :return: GCodeEffect instance; effect the gcode just had on machine
        """
        from .machine import Machine  # importing high-level state
        assert isinstance(machine, Machine), "invalid parameter"

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


class GCodeArcMoveCW(GCodeArcMove):
    """G2: Arc Move (clockwise)"""
    word_key = Word('G', 2)


class GCodeArcMoveCCW(GCodeArcMove):
    """G3: Arc Move (counter-clockwise)"""
    word_key = Word('G', 3)


class GCodeDwell(GCodeMotion):
    """G4: Dwell"""
    param_letters = GCodeMotion.param_letters | set('P')
    word_key = Word('G', 4)
    modal_group = None  # one of the few motion commands that isn't modal
    exec_order = 140


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


class GCodeDrillingCycle(GCodeCannedCycle):
    """G81: Drilling Cycle"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 81)


class GCodeDrillingCycleDwell(GCodeCannedCycle):
    """G82: Drilling Cycle, Dwell"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 82)


class GCodeDrillingCyclePeck(GCodeCannedCycle):
    """G83: Drilling Cycle, Peck"""
    param_letters = GCodeCannedCycle.param_letters | set('RLQ')
    word_key = Word('G', 83)


class GCodeDrillingCycleChipBreaking(GCodeCannedCycle):
    """G73: Drilling Cycle, ChipBreaking"""
    param_letters = GCodeCannedCycle.param_letters | set('RLQ')
    word_key = Word('G', 73)


class GCodeBoringCycleFeedOut(GCodeCannedCycle):
    """G85: Boring Cycle, Feed Out"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 85)


class GCodeBoringCycleDwellFeedOut(GCodeCannedCycle):
    """G89: Boring Cycle, Dwell, Feed Out"""
    param_letters = GCodeCannedCycle.param_letters | set('RLP')
    word_key = Word('G', 89)


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
    exec_order = 90


class GCodeStartSpindleCW(GCodeSpindle):
    """M3: Start Spindle Clockwise"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 3)
    modal_group = MODAL_GROUP_MAP['spindle']

class GCodeStartSpindleCCW(GCodeSpindle):
    """M4: Start Spindle Counter-Clockwise"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 4)
    modal_group = MODAL_GROUP_MAP['spindle']


class GCodeStopSpindle(GCodeSpindle):
    """M5: Stop Spindle"""
    #param_letters = set('S')  # S is it's own gcode, makes no sense to be here
    word_key = Word('M', 5)
    modal_group = MODAL_GROUP_MAP['spindle']


class GCodeOrientSpindle(GCodeSpindle):
    """M19: Orient Spindle"""
    word_key = Word('M', 19)


class GCodeSpindleConstantSurfaceSpeedMode(GCodeSpindle):
    """G96: Spindle Constant Surface Speed"""
    param_letters = set('DS')
    word_key = Word('G', 96)
    modal_group = MODAL_GROUP_MAP['spindle_speed_mode']


class GCodeSpindleRPMMode(GCodeSpindle):
    """G97: Spindle RPM Speed"""
    param_letters = set('D')
    word_key = Word('G', 97)
    modal_group = MODAL_GROUP_MAP['spindle_speed_mode']



# ======================= Coolant =======================
# CODE              PARAMETERS          DESCRIPTION
# M7, M8, M9                            Coolant Control

class GCodeCoolant(GCode):
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


class GCodeSelectXYPlane(GCodePlaneSelect):
    """G17: select XY plane (default)"""
    word_key = Word('G', 17)


class GCodeSelectZXPlane(GCodePlaneSelect):
    """G18: select ZX plane"""
    word_key = Word('G', 18)


class GCodeSelectYZPlane(GCodePlaneSelect):
    """G19: select YZ plane"""
    word_key = Word('G', 19)


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
# G98                                   Canned Cycle Return Level

class GCodeCannedReturnMode(GCode):
    modal_group = MODAL_GROUP_MAP['canned_cycles_return']
    exec_order = 220


class GCodeCannedCycleReturnLevel(GCodeCannedReturnMode):
    """G98: Canned Cycle Return Level"""
    word_key = Word('G', 98)


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
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'F'
    modal_group = MODAL_GROUP_MAP['feed_rate']
    exec_order = 40


class GCodeSpindleSpeed(GCodeOtherModal):
    """S: Set Spindle Speed"""
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'S'
    # Modal Group: (see description in GCodeFeedRate)
    modal_group = MODAL_GROUP_MAP['spindle_speed']
    exec_order = 50


class GCodeSelectTool(GCodeOtherModal):
    """T: Select Tool"""
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'T'
    # Modal Group: (see description in GCodeFeedRate)
    modal_group = MODAL_GROUP_MAP['tool']
    exec_order = 60


class GCodeSpeedAndFeedOverrideOn(GCodeOtherModal):
    """M48: Speed and Feed Override Control On"""
    word_key = Word('M', 48)
    modal_group = MODAL_GROUP_MAP['override_switches']
    exec_order = 120


class GCodeSpeedAndFeedOverrideOff(GCodeOtherModal):
    """M49: Speed and Feed Override Control Off"""
    word_key = Word('M', 49)
    modal_group = MODAL_GROUP_MAP['override_switches']
    exec_order = 120


class GCodeFeedOverride(GCodeOtherModal):
    """M50: Feed Override Control"""
    param_letters = set('P')
    word_key = Word('M', 50)
    exec_order = 120


class GCodeSpindleSpeedOverride(GCodeOtherModal):
    """M51: Spindle Speed Override Control"""
    param_letters = set('P')
    word_key = Word('M', 51)
    exec_order = 120


class GCodeAdaptiveFeed(GCodeOtherModal):
    """M52: Adaptive Feed Control"""
    param_letters = set('P')
    word_key = Word('M', 52)
    exec_order = 120


class GCodeFeedStop(GCodeOtherModal):
    """M53: Feed Stop Control"""
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
    exec_order = 80


class GCodeToolSetCurrent(GCodeNonModal):
    """M61: Set Current Tool"""
    param_letters = set('Q')
    word_key = Word('M', 61)
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
    exec_order = 230


class GCodeSetPredefinedPosition(GCodeNonModal):
    """G28.1,G30.1: Set Predefined Position"""  # redundancy in language there, but I'll let it slide
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [28.1, 30.1])
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
    exec_order = 230

    # TODO: machine.state.offset *= 0


class GCodeRestoreCoordSystemOffset(GCodeNonModal):
    """G92.3: Restore Coordinate System Offset"""
    word_key = Word('G', 92.3)
    exec_order = 230


class GCodeUserDefined(GCodeNonModal):
    """M101-M199: User Defined Commands"""
    # To create user g-codes, inherit from this class
    param_letters = set('PQ')
    #@classmethod
    #def word_matches(cls, w):
    #    return (w.letter == 'M') and (101 <= w.value <= 199)
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


def _gcode_class_infostr(base_class=GCode):
    """
    List all ineheriting classes for the given gcode class
    :param base_class: root of hierarcy
    :return: str listing all gcode classes
    """
    info_str = ""
    for (cls, level) in _subclasses_level(base_class):
        word_str = ''
        if cls.word_key:
            word_str = cls.word_key.clean_str
        info_str += "{word} {indent}- {name}: {description}\n".format(
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


def word_gcode_class(word, exhaustive=False):
    """
    Map word to corresponding GCode class
    :param word: Word instance
    :param exhausitve: if True, all words are tested; not just 'GMFST'
    :return: class inheriting GCode
    """

    if _gcode_maps_created is False:
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
