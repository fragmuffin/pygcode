# Unsupported Files

Files containing unsupported gcodes

We can however still deal with these, workarounds shown below

## Unsupported GCodes

When attempting to process unsupported gcode(s) via a `Machine` the following error (or similar) will be raised

    MachineInvalidState: unsupported gcode(s): 'P1 M10' (machine mode: <Mode: G00 G17 G90 G90.1 G94 G21 G40 G49 G54 G61 G97 M05 M09 F600 S0 T0>)


These codes are not currently supported by this library, but you may introduce
them for your project. with the following workaround

**Workaround**

Any class inheriting `GCode` is used to parse each gcode string.

Look to the root `GCode` class definition in `gcodes.py` for more details.

So, create the following class(es) (anywhere in your codebase, as long as it's
imported)


### `M10` / `M11` : Pallet Clamp

    import pygcode

    class GCodePalletClampOn(pygcode.GCode):
        """M10: Pallet clamp on"""
        word_key = pygcode.Word('M', 10)
        word_letter = 'M'
        param_letters = set('P')

    class GCodePalletClampOff(pygcode.GCode):
        """M10: Pallet clamp off"""
        word_key = pygcode.Word('M', 11)
        word_letter = 'M'
        param_letters = set('P')


### `G70` / `G71` : Fixed cycle, multiple repetitive cycle

    import pygcode

    class GCodeFixedCycleMultiRepCycleRough(pygcode.GCode):
        """G70: Fixed cycle, multiple repetitive cycle, for finishing (including contours)"""
        word_key = pygcode.Word('G', 70)
        word_letter = 'G'

    class GCodeFixedCycleMultiRepCycleRough(pygcode.GCode):
        """G71: Fixed cycle, multiple repetitive cycle, for roughing (Z-axis emphasis)"""
        word_key = pygcode.Word('G', 71)
        word_letter = 'G'
