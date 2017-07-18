# =========================== Package Information ===========================
# Version Planning:
#   0.1.x               - Development Status :: 2 - Pre-Alpha
#   0.2.x               - Development Status :: 3 - Alpha
#   0.3.x               - Development Status :: 4 - Beta
#   1.x                 - Development Status :: 5 - Production/Stable
#   <any above>.y       - developments on that version (pre-release)
#   <any above>*.dev*   - development release (intended purely to test deployment)
__version__ = "0.1.0"

__title__ = "pygcode"
__description__ = "Basic g-code parser, interpreter, and encoder library."
__url__ = "https://github.com/fragmuffin/pygcode"

__author__ = "Peter Boin"
__email__ = "peter.boin@gmail.com"

__license__ = "GPLv3"

# not text-parsable
__copyright__ = "Copyright (c) 2017 {0}".format(__author__)


# =========================== Imports ===========================
__all__ = [
    # Machine
    'Machine', 'Position', 'CoordinateSystem', 'State', 'Mode',
    # Line
    'Line',
    # Block
    'Block',
    # Comment
    'Comment', 'split_line',
    # Word
    'Word', 'text2words', 'str2word', 'words2dict',

    # GCodes
    'words2gcodes', 'text2gcodes', 'split_gcodes',
    # $ python -c "from pygcode.gcodes import GCode, _subclasses as sc; print(',\\n    '.join(sorted('\\'%s\\'' % g.__name__ for g in sc(GCode))))"
    'GCode',
    'GCodeAbsoluteArcDistanceMode',
    'GCodeAbsoluteDistanceMode',
    'GCodeAdaptiveFeed',
    'GCodeAddToolLengthOffset',
    'GCodeAnalogOutput',
    'GCodeAnalogOutputImmediate',
    'GCodeAnalogOutputSyncd',
    'GCodeArcMove',
    'GCodeArcMoveCCW',
    'GCodeArcMoveCW',
    'GCodeBoringCycleDwellFeedOut',
    'GCodeBoringCycleFeedOut',
    'GCodeCancelCannedCycle',
    'GCodeCancelToolLengthOffset',
    'GCodeCannedCycle',
    'GCodeCannedCycleReturnLevel',
    'GCodeCannedCycleReturnToR',
    'GCodeCannedReturnMode',
    'GCodeCoolant',
    'GCodeCoolantFloodOn',
    'GCodeCoolantMistOn',
    'GCodeCoolantOff',
    'GCodeCoordSystemOffset',
    'GCodeCublcSpline',
    'GCodeCutterCompLeft',
    'GCodeCutterCompRight',
    'GCodeCutterRadiusComp',
    'GCodeCutterRadiusCompOff',
    'GCodeDigitalOutput',
    'GCodeDigitalOutputOff',
    'GCodeDigitalOutputOffSyncd',
    'GCodeDigitalOutputOn',
    'GCodeDigitalOutputOnSyncd',
    'GCodeDistanceMode',
    'GCodeDrillingCycle',
    'GCodeDrillingCycleChipBreaking',
    'GCodeDrillingCycleDwell',
    'GCodeDrillingCyclePeck',
    'GCodeDwell',
    'GCodeDynamicCutterCompLeft',
    'GCodeDynamicCutterCompRight',
    'GCodeDynamicToolLengthOffset',
    'GCodeEndProgram',
    'GCodeEndProgramPalletShuttle',
    'GCodeExactPathMode',
    'GCodeExactStopMode',
    'GCodeFeedOverride',
    'GCodeFeedRate',
    'GCodeFeedRateMode',
    'GCodeFeedStop',
    'GCodeGotoPredefinedPosition',
    'GCodeIO',
    'GCodeIncrementalArcDistanceMode',
    'GCodeIncrementalDistanceMode',
    'GCodeInverseTimeMode',
    'GCodeLatheDiameterMode',
    'GCodeLatheRadiusMode',
    'GCodeLinearMove',
    'GCodeMotion',
    'GCodeMoveInMachineCoords',
    'GCodeNURBS',
    'GCodeNURBSEnd',
    'GCodeNonModal',
    'GCodeOrientSpindle',
    'GCodeOtherModal',
    'GCodePalletChangePause',
    'GCodePathBlendingMode',
    'GCodePathControlMode',
    'GCodePauseProgram',
    'GCodePauseProgramOptional',
    'GCodePlaneSelect',
    'GCodeProgramControl',
    'GCodeQuadraticSpline',
    'GCodeRapidMove',
    'GCodeResetCoordSystemOffset',
    'GCodeRestoreCoordSystemOffset',
    'GCodeRigidTapping',
    'GCodeSelectCoordinateSystem',
    'GCodeSelectCoordinateSystem1',
    'GCodeSelectCoordinateSystem2',
    'GCodeSelectCoordinateSystem3',
    'GCodeSelectCoordinateSystem4',
    'GCodeSelectCoordinateSystem5',
    'GCodeSelectCoordinateSystem6',
    'GCodeSelectCoordinateSystem7',
    'GCodeSelectCoordinateSystem8',
    'GCodeSelectCoordinateSystem9',
    'GCodeSelectTool',
    'GCodeSelectUVPlane',
    'GCodeSelectVWPlane',
    'GCodeSelectWUPlane',
    'GCodeSelectXYPlane',
    'GCodeSelectYZPlane',
    'GCodeSelectZXPlane',
    'GCodeSet',
    'GCodeSetPredefinedPosition',
    'GCodeSpeedAndFeedOverrideOff',
    'GCodeSpeedAndFeedOverrideOn',
    'GCodeSpindle',
    'GCodeSpindleConstantSurfaceSpeedMode',
    'GCodeSpindleRPMMode',
    'GCodeSpindleSpeed',
    'GCodeSpindleSpeedMode',
    'GCodeSpindleSpeedOverride',
    'GCodeSpindleSyncMotion',
    'GCodeStartSpindle',
    'GCodeStartSpindleCCW',
    'GCodeStartSpindleCW',
    'GCodeStopSpindle',
    'GCodeStraightProbe',
    'GCodeThreadingCycle',
    'GCodeToolChange',
    'GCodeToolLength',
    'GCodeToolLengthOffset',
    'GCodeToolSetCurrent',
    'GCodeUnit',
    'GCodeUnitsPerMinuteMode',
    'GCodeUnitsPerRevolution',
    'GCodeUseInches',
    'GCodeUseMillimeters',
    'GCodeUserDefined',
    'GCodeWaitOnInput'
]

# Machine
from .machine import (
    Position, CoordinateSystem,
    State, Mode,
    Machine,
)

# Line
from .line import Line

# Block
from .block import Block

# Comment
from .comment import Comment, split_line

# Word
from .words import (
    Word,
    text2words, str2word, words2dict,
)

# GCode
from .gcodes import (
    words2gcodes, text2gcodes, split_gcodes,

    # $ python -c "from pygcode.gcodes import _gcode_class_infostr as x; print(x(prefix='    # '))"
    #       - GCode:
    #         - GCodeCannedCycle:
    # G89       - GCodeBoringCycleDwellFeedOut: G89: Boring Cycle, Dwell, Feed Out
    # G85       - GCodeBoringCycleFeedOut: G85: Boring Cycle, Feed Out
    # G81       - GCodeDrillingCycle: G81: Drilling Cycle
    # G73       - GCodeDrillingCycleChipBreaking: G73: Drilling Cycle, ChipBreaking
    # G82       - GCodeDrillingCycleDwell: G82: Drilling Cycle, Dwell
    # G83       - GCodeDrillingCyclePeck: G83: Drilling Cycle, Peck
    # G76       - GCodeThreadingCycle: G76: Threading Cycle
    #         - GCodeCannedReturnMode:
    # G98       - GCodeCannedCycleReturnLevel: G98: Canned Cycle Return to the level set prior to cycle start
    # G99       - GCodeCannedCycleReturnToR: G99: Canned Cycle Return to the level set by R
    #         - GCodeCoolant:
    # M08       - GCodeCoolantFloodOn: M8: turn flood coolant on
    # M07       - GCodeCoolantMistOn: M7: turn mist coolant on
    # M09       - GCodeCoolantOff: M9: turn all coolant off
    #         - GCodeCutterRadiusComp:
    # G41       - GCodeCutterCompLeft: G41: Cutter Radius Compensation (left)
    # G42       - GCodeCutterCompRight: G42: Cutter Radius Compensation (right)
    # G40       - GCodeCutterRadiusCompOff: G40: Cutter Radius Compensation Off
    # G41.1     - GCodeDynamicCutterCompLeft: G41.1: Dynamic Cutter Radius Compensation (left)
    # G42.1     - GCodeDynamicCutterCompRight: G42.1: Dynamic Cutter Radius Compensation (right)
    #         - GCodeDistanceMode:
    # G90.1     - GCodeAbsoluteArcDistanceMode: G90.1: Absolute Distance Mode for Arc IJK Parameters
    # G90       - GCodeAbsoluteDistanceMode: G90: Absolute Distance Mode
    # G91.1     - GCodeIncrementalArcDistanceMode: G91.1: Incremental Distance Mode for Arc IJK Parameters
    # G91       - GCodeIncrementalDistanceMode: G91: Incremental Distance Mode
    # G07       - GCodeLatheDiameterMode: G7: Lathe Diameter Mode
    # G08       - GCodeLatheRadiusMode: G8: Lathe Radius Mode
    #         - GCodeFeedRateMode:
    # G93       - GCodeInverseTimeMode: G93: Inverse Time Mode
    # G94       - GCodeUnitsPerMinuteMode: G94: Units Per MinuteMode
    # G95       - GCodeUnitsPerRevolution: G95: Units Per Revolution
    #         - GCodeIO:
    #           - GCodeAnalogOutput: Analog Output
    # M68         - GCodeAnalogOutputImmediate: M68: Analog Output, Immediate
    # M67         - GCodeAnalogOutputSyncd: M67: Analog Output, Synchronized
    #           - GCodeDigitalOutput: Digital Output Control
    # M65         - GCodeDigitalOutputOff: M65: turn off digital output immediately
    # M63         - GCodeDigitalOutputOffSyncd: M63: turn off digital output synchronized with motion
    # M64         - GCodeDigitalOutputOn: M64: turn on digital output immediately
    # M62         - GCodeDigitalOutputOnSyncd: M62: turn on digital output synchronized with motion
    # M66       - GCodeWaitOnInput: M66: Wait on Input
    #         - GCodeMotion:
    #           - GCodeArcMove: Arc Move
    # G03         - GCodeArcMoveCCW: G3: Arc Move (counter-clockwise)
    # G02         - GCodeArcMoveCW: G2: Arc Move (clockwise)
    # G80       - GCodeCancelCannedCycle: G80: Cancel Canned Cycle
    # G05       - GCodeCublcSpline: G5: Cubic Spline
    # G04       - GCodeDwell: G4: Dwell
    # G01       - GCodeLinearMove: G1: Linear Move
    # G05.2     - GCodeNURBS: G5.2: Non-uniform rational basis spline (NURBS)
    # G05.3       - GCodeNURBSEnd: G5.3: end NURBS mode
    # G05.1     - GCodeQuadraticSpline: G5.1: Quadratic Spline
    # G00       - GCodeRapidMove: G0: Rapid Move
    # G33.1     - GCodeRigidTapping: G33.1: Rigid Tapping
    # G33       - GCodeSpindleSyncMotion: G33: Spindle Synchronized Motion
    #           - GCodeStraightProbe: G38.2-G38.5: Straight Probe
    #         - GCodeNonModal:
    # G92       - GCodeCoordSystemOffset: G92: Coordinate System Offset
    #           - GCodeGotoPredefinedPosition: G28,G30: Goto Predefined Position (rapid movement)
    # G53       - GCodeMoveInMachineCoords: G53: Move in Machine Coordinates
    #           - GCodeResetCoordSystemOffset: G92.1,G92.2: Reset Coordinate System Offset
    # G92.3     - GCodeRestoreCoordSystemOffset: G92.3: Restore Coordinate System Offset
    # G10       - GCodeSet: G10: Set stuff
    #           - GCodeSetPredefinedPosition: G28.1,G30.1: Set Predefined Position
    # M06       - GCodeToolChange: M6: Tool Change
    # M61       - GCodeToolSetCurrent: M61: Set Current Tool
    #           - GCodeUserDefined: M101-M199: User Defined Commands
    #         - GCodeOtherModal:
    # M52       - GCodeAdaptiveFeed: M52: Adaptive Feed Control
    # M50       - GCodeFeedOverride: M50: Feed Override Control
    #           - GCodeFeedRate: F: Set Feed Rate
    # M53       - GCodeFeedStop: M53: Feed Stop Control
    #           - GCodeSelectCoordinateSystem: Select Coordinate System
    # G54         - GCodeSelectCoordinateSystem1: Select Coordinate System 1
    # G55         - GCodeSelectCoordinateSystem2: Select Coordinate System 2
    # G56         - GCodeSelectCoordinateSystem3: Select Coordinate System 3
    # G57         - GCodeSelectCoordinateSystem4: Select Coordinate System 4
    # G58         - GCodeSelectCoordinateSystem5: Select Coordinate System 5
    # G59         - GCodeSelectCoordinateSystem6: Select Coordinate System 6
    # G59.1       - GCodeSelectCoordinateSystem7: Select Coordinate System 7
    # G59.2       - GCodeSelectCoordinateSystem8: Select Coordinate System 8
    # G59.3       - GCodeSelectCoordinateSystem9: Select Coordinate System 9
    #           - GCodeSelectTool: T: Select Tool
    # M49       - GCodeSpeedAndFeedOverrideOff: M49: Speed and Feed Override Control Off
    # M48       - GCodeSpeedAndFeedOverrideOn: M48: Speed and Feed Override Control On
    #           - GCodeSpindleSpeed: S: Set Spindle Speed
    # M51       - GCodeSpindleSpeedOverride: M51: Spindle Speed Override Control
    #         - GCodePathControlMode:
    # G61       - GCodeExactPathMode: G61: Exact path mode
    # G61.1     - GCodeExactStopMode: G61.1: Exact stop mode
    # G64       - GCodePathBlendingMode: G64: Path Blending
    #         - GCodePlaneSelect:
    # G17.1     - GCodeSelectUVPlane: G17.1: select UV plane
    # G19.1     - GCodeSelectVWPlane: G19.1: select VW plane
    # G18.1     - GCodeSelectWUPlane: G18.1: select WU plane
    # G17       - GCodeSelectXYPlane: G17: select XY plane (default)
    # G19       - GCodeSelectYZPlane: G19: select YZ plane
    # G18       - GCodeSelectZXPlane: G18: select ZX plane
    #         - GCodeProgramControl:
    # M02       - GCodeEndProgram: M2: Program End
    # M30       - GCodeEndProgramPalletShuttle: M30: exchange pallet shuttles and end the program
    # M60       - GCodePalletChangePause: M60: Pallet Change Pause
    # M00       - GCodePauseProgram: M0: Program Pause
    # M01       - GCodePauseProgramOptional: M1: Program Pause (optional)
    #         - GCodeSpindle:
    # M19       - GCodeOrientSpindle: M19: Orient Spindle
    #           - GCodeSpindleSpeedMode:
    # G96         - GCodeSpindleConstantSurfaceSpeedMode: G96: Spindle Constant Surface Speed
    # G97         - GCodeSpindleRPMMode: G97: Spindle RPM Speed
    #           - GCodeStartSpindle: M3,M4: Start Spindle Clockwise
    # M04         - GCodeStartSpindleCCW: M4: Start Spindle Counter-Clockwise
    # M03         - GCodeStartSpindleCW: M3: Start Spindle Clockwise
    # M05       - GCodeStopSpindle: M5: Stop Spindle
    #         - GCodeToolLength:
    # G43.2     - GCodeAddToolLengthOffset: G43.2: Appkly Additional Tool Length Offset
    # G49       - GCodeCancelToolLengthOffset: G49: Cancel Tool Length Compensation
    # G43.1     - GCodeDynamicToolLengthOffset: G43.1: Dynamic Tool Length Offset
    # G43       - GCodeToolLengthOffset: G43: Tool Length Offset
    #         - GCodeUnit:
    # G20       - GCodeUseInches: G20: use inches for length units
    # G21       - GCodeUseMillimeters: G21: use millimeters for length units

    # $ python -c "from pygcode.gcodes import GCode, _subclasses as sc; print(',\\n    '.join(sorted(g.__name__ for g in sc(GCode))))"
    GCode,
    GCodeAbsoluteArcDistanceMode,
    GCodeAbsoluteDistanceMode,
    GCodeAdaptiveFeed,
    GCodeAddToolLengthOffset,
    GCodeAnalogOutput,
    GCodeAnalogOutputImmediate,
    GCodeAnalogOutputSyncd,
    GCodeArcMove,
    GCodeArcMoveCCW,
    GCodeArcMoveCW,
    GCodeBoringCycleDwellFeedOut,
    GCodeBoringCycleFeedOut,
    GCodeCancelCannedCycle,
    GCodeCancelToolLengthOffset,
    GCodeCannedCycle,
    GCodeCannedCycleReturnLevel,
    GCodeCannedCycleReturnToR,
    GCodeCannedReturnMode,
    GCodeCoolant,
    GCodeCoolantFloodOn,
    GCodeCoolantMistOn,
    GCodeCoolantOff,
    GCodeCoordSystemOffset,
    GCodeCublcSpline,
    GCodeCutterCompLeft,
    GCodeCutterCompRight,
    GCodeCutterRadiusComp,
    GCodeCutterRadiusCompOff,
    GCodeDigitalOutput,
    GCodeDigitalOutputOff,
    GCodeDigitalOutputOffSyncd,
    GCodeDigitalOutputOn,
    GCodeDigitalOutputOnSyncd,
    GCodeDistanceMode,
    GCodeDrillingCycle,
    GCodeDrillingCycleChipBreaking,
    GCodeDrillingCycleDwell,
    GCodeDrillingCyclePeck,
    GCodeDwell,
    GCodeDynamicCutterCompLeft,
    GCodeDynamicCutterCompRight,
    GCodeDynamicToolLengthOffset,
    GCodeEndProgram,
    GCodeEndProgramPalletShuttle,
    GCodeExactPathMode,
    GCodeExactStopMode,
    GCodeFeedOverride,
    GCodeFeedRate,
    GCodeFeedRateMode,
    GCodeFeedStop,
    GCodeGotoPredefinedPosition,
    GCodeIO,
    GCodeIncrementalArcDistanceMode,
    GCodeIncrementalDistanceMode,
    GCodeInverseTimeMode,
    GCodeLatheDiameterMode,
    GCodeLatheRadiusMode,
    GCodeLinearMove,
    GCodeMotion,
    GCodeMoveInMachineCoords,
    GCodeNURBS,
    GCodeNURBSEnd,
    GCodeNonModal,
    GCodeOrientSpindle,
    GCodeOtherModal,
    GCodePalletChangePause,
    GCodePathBlendingMode,
    GCodePathControlMode,
    GCodePauseProgram,
    GCodePauseProgramOptional,
    GCodePlaneSelect,
    GCodeProgramControl,
    GCodeQuadraticSpline,
    GCodeRapidMove,
    GCodeResetCoordSystemOffset,
    GCodeRestoreCoordSystemOffset,
    GCodeRigidTapping,
    GCodeSelectCoordinateSystem,
    GCodeSelectCoordinateSystem1,
    GCodeSelectCoordinateSystem2,
    GCodeSelectCoordinateSystem3,
    GCodeSelectCoordinateSystem4,
    GCodeSelectCoordinateSystem5,
    GCodeSelectCoordinateSystem6,
    GCodeSelectCoordinateSystem7,
    GCodeSelectCoordinateSystem8,
    GCodeSelectCoordinateSystem9,
    GCodeSelectTool,
    GCodeSelectUVPlane,
    GCodeSelectVWPlane,
    GCodeSelectWUPlane,
    GCodeSelectXYPlane,
    GCodeSelectYZPlane,
    GCodeSelectZXPlane,
    GCodeSet,
    GCodeSetPredefinedPosition,
    GCodeSpeedAndFeedOverrideOff,
    GCodeSpeedAndFeedOverrideOn,
    GCodeSpindle,
    GCodeSpindleConstantSurfaceSpeedMode,
    GCodeSpindleRPMMode,
    GCodeSpindleSpeed,
    GCodeSpindleSpeedMode,
    GCodeSpindleSpeedOverride,
    GCodeSpindleSyncMotion,
    GCodeStartSpindle,
    GCodeStartSpindleCCW,
    GCodeStartSpindleCW,
    GCodeStopSpindle,
    GCodeStraightProbe,
    GCodeThreadingCycle,
    GCodeToolChange,
    GCodeToolLength,
    GCodeToolLengthOffset,
    GCodeToolSetCurrent,
    GCodeUnit,
    GCodeUnitsPerMinuteMode,
    GCodeUnitsPerRevolution,
    GCodeUseInches,
    GCodeUseMillimeters,
    GCodeUserDefined,
    GCodeWaitOnInput
)
