from collections import defaultdict

from .words import Word


class GCode(object):
    # Defining Word
    word_key = None # Word instance to use in lookup
    word_matches = None # function (secondary)
    # Parameters associated to this gcode
    param_letters = set()

    def __init__(self, word, *params):
        assert isinstance(word, Word), "invalid gcode word %r" % code_word
        self.word = word
        self.params = {}

        # Add Given Parameters
        for param in params:
            self.add_parameter(param)

    def __repr__(self):
        return "<{class_name}: {gcode}{{{word_list}}}>".format(
            class_name=self.__class__.__name__,
            gcode=self.word,
            word_list=', '.join([
                "{}".format(self.params[k])
                for k in sorted(self.params.keys())
            ]),
        )

    def __str__(self):
        """String representation of gcode, as it would be seen in a .gcode file"""
        return "{gcode} {parameters}".format(
            gcode=self.word,
            parameters=' '.join([
                "{}".format(self.params[k])
                for k in sorted(self.params.keys())
            ]),
        )

    def add_parameter(self, word):
        assert isinstance(word, Word), "invalid parameter class: %r" % word
        assert word.letter in self.param_letters, "invalid parameter for %s: %s" % (self.__class__.__name__, str(word))
        assert word.letter not in self.params, "parameter defined twice: %s -> %s" % (self.params[word.letter], word)
        self.params[word.letter] = word

    def __getattr__(self, key):
        if key in self.param_letters:
            if key in self.params:
                return self.params[key].value
            else:
                return None # parameter is valid for GCode, but undefined

        raise AttributeError("'{cls}' object has no attribute '{key}'".format(
            cls=self.__class__.__name__,
            key=key
        ))


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


class GCodeRapidMove(GCodeMotion):
    """G0: Rapid Move"""
    word_key = Word('G', 0)


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
    pass


class GCodeAbsoluteDistanceMode(GCodeDistanceMode):
    """G90: Absolute Distance Mode"""
    word_key = Word('G', 90)


class GCodeIncrementalDistanceMode(GCodeDistanceMode):
    """G91: Incremental Distance Mode"""
    word_key = Word('G', 91)


class GCodeAbsoluteArcDistanceMode(GCodeDistanceMode):
    """G90.1: Absolute Distance Mode for Arc IJK Parameters"""
    word_key = Word('G', 90.1)


class GCodeIncrementalArcDistanceMode(GCodeDistanceMode):
    """G91.1: Incremental Distance Mode for Arc IJK Parameters"""
    word_key = Word('G', 91.1)


class GCodeLatheDiameterMode(GCodeDistanceMode):
    """G7: Lathe Diameter Mode"""
    word_key = Word('G', 7)


class GCodeLatheRadiusMode(GCodeDistanceMode):
    """G8: Lathe Radius Mode"""
    word_key = Word('G', 8)


# ======================= Feed Rate Mode =======================
# CODE              PARAMETERS          DESCRIPTION
# G93, G94, G95                         Feed Rate Mode

class GCodeFeedRateMode(GCode):
    pass


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
    pass


class GCodeStartSpindleCW(GCodeSpindle):
    """M3: Start Spindle Clockwise"""
    param_letters = set('S')
    word_key = Word('M', 3)


class GCodeStartSpindleCCW(GCodeSpindle):
    """M4: Start Spindle Counter-Clockwise"""
    param_letters = set('S')
    word_key = Word('M', 4)


class GCodeStopSpindle(GCodeSpindle):
    """M5: Stop Spindle"""
    param_letters = set('S')
    word_key = Word('M', 5)


class GCodeOrientSpindle(GCodeSpindle):
    """M19: Orient Spindle"""
    word_key = Word('M', 19)


class GCodeSpindleConstantSurfaceSpeedMode(GCodeSpindle):
    """G96: Spindle Constant Surface Speed"""
    param_letters = set('DS')
    word_key = Word('G', 96)


class GCodeSpindleRPMMode(GCodeSpindle):
    """G97: Spindle RPM Speed"""
    param_letters = set('D')
    word_key = Word('G', 97)



# ======================= Coolant =======================
# CODE              PARAMETERS          DESCRIPTION
# M7, M8, M9                            Coolant Control

class GCodeCoolant(GCode):
    pass


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
    pass


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
    pass


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
    pass

class GCodeUseInches(GCodeUnit):
    """G20: use inches for length units"""
    word_key = Word('G', 20)

class GCodeUseMillimeters(GCodeUnit):
    """G21: use millimeters for length units"""
    word_key = Word('G', 21)


# ======================= Plane Selection =======================
#       (affects G2, G3, G81-G89, G40-G42)
# CODE              PARAMETERS          DESCRIPTION
# G17 - G19.1                           Plane Select

class GCodePlaneSelect(GCode):
    pass


class GCodeSelectZYPlane(GCodePlaneSelect):
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
    pass


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
    pass


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
    pass


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

class GCodeSpindleSpeed(GCodeOtherModal):
    """S: Set Spindle Speed"""
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'S'


class GCodeSelectTool(GCodeOtherModal):
    """T: Select Tool"""
    @classmethod
    def word_matches(cls, w):
        return w.letter == 'T'


class GCodeSpeedAndFeedOverrideOn(GCodeOtherModal):
    """M48: Speed and Feed Override Control On"""
    word_key = Word('M', 48)


class GCodeSpeedAndFeedOverrideOff(GCodeOtherModal):
    """M49: Speed and Feed Override Control Off"""
    word_key = Word('M', 49)


class GCodeFeedOverride(GCodeOtherModal):
    """M50: Feed Override Control"""
    param_letters = set('P')
    word_key = Word('M', 50)


class GCodeSpindleSpeedOverride(GCodeOtherModal):
    """M51: Spindle Speed Override Control"""
    param_letters = set('P')
    word_key = Word('M', 51)


class GCodeAdaptiveFeed(GCodeOtherModal):
    """M52: Adaptive Feed Control"""
    param_letters = set('P')
    word_key = Word('M', 52)


class GCodeFeedStop(GCodeOtherModal):
    """M53: Feed Stop Control"""
    param_letters = set('P')
    word_key = Word('M', 53)


class GCodeSelectCoordinateSystem(GCodeOtherModal):
    """
    G54   - select coordinate system 1
    G55   - select coordinate system 2
    G56   - select coordinate system 3
    G57   - select coordinate system 4
    G58   - select coordinate system 5
    G59   - select coordinate system 6
    G59.1 - select coordinate system 7
    G59.2 - select coordinate system 8
    G59.3 - select coordinate system 9
    """
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [54, 55, 56, 57, 58, 59, 59.1, 59.2, 59.3])


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
    pass


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


class GCodeToolSetCurrent(GCodeNonModal):
    """M61: Set Current Tool"""
    param_letters = set('Q')
    word_key = Word('M', 61)


class GCodeSet(GCodeNonModal):
    """G10: Set stuff"""
    param_letters = set('LPQR')
    word_key = Word('G', 10)


class GCodeGotoPredefinedPosition(GCodeNonModal):
    """G28,G30: Goto Predefined Position (rapid movement)"""
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [28, 30])


class GCodeSetPredefinedPosition(GCodeNonModal):
    """G28.1,G30.1: Set Predefined Position"""  # redundancy in language there, but I'll let it slide
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [28.1, 30.1])


class GCodeMoveInMachineCoords(GCodeNonModal):
    """G53: Move in Machine Coordinates"""
    word_key = Word('G', 53)


class GCodeCoordSystemOffset(GCodeNonModal):
    """G92: Coordinate System Offset"""
    word_key = Word('G', 92)


class GCodeResetCoordSystemOffset(GCodeNonModal):
    """G92.1,G92.2: Reset Coordinate System Offset"""
    @classmethod
    def word_matches(cls, w):
        return (w.letter == 'G') and (w.value in [92.1, 92.2])


class GCodeRestoreCoordSystemOffset(GCodeNonModal):
    """G92.3: Restore Coordinate System Offset"""
    word_key = Word('G', 92.3)


class GCodeUserDefined(GCodeNonModal):
    """M101-M199: User Defined Commands"""
    # To create user g-codes, inherit from this class
    param_letters = set('PQ')
    #@classmethod
    #def word_matches(cls, w):
    #    return (w.letter == 'M') and (101 <= w.value <= 199)


# ======================= Utilities =======================

def _subclasses_level(root_class, recursion_level=0):
    """
    Hierarcical list of all classes inheriting from the given root class (recursive)
    :param root_class: class used as trunk of hierarchy (included inoutput)
    :param recursion_level: should always be 0 (unless recursively called)
    :param
    """
    yield (root_class, recursion_level)
    for cls in root_class.__subclasses__():
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
        info_str += "{indent}- {name}: {description}\n".format(
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
    # Ensure lists are clear
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


def words_to_gcodes(words):
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
