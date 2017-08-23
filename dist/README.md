# Change History

----
## 0.2.1

### Improvements

**`pygcode-norm` script:**

Added "Final Machine Actions:"

    Final Machine Actions:
      standardize what's done at the end of a gcode program.

      --zero_xy, -zxy       On completion, move straight up to
                            rapid_safety_height, then across to X0 Y0.
      --zero_z, -zz         On completion, move down to Z0 (done after zero_xy, if
                            set).
      --rapid_safety_height RAPID_SAFETY_HEIGHT, -rsh RAPID_SAFETY_HEIGHT
                            Z value to move to before traversing workpiece (if not
                            set, max value will be attempted).
      --spindle_off, -so    On completion, turn spindle off.


Added ability to remove all codes & parameters that cannot be parsed.

      --rm_invalid_modal, -rmim
                            Simply remove everything that isn't understood. Use
                            with caution.

**Library Improvements**

* `Machine.abs2work(<Position>)` and `Machine.work2abs(<Position>)` position
  converters, apply machine's offset to the given position without effecting
  machine's current position.
* `Machine.clean_block(<Block>)` removes content from a block that's not parsable (use with caution)
* `Machine.ignore_invalid_modal` bool class parameter, if set, will continue on merrily while ignoring
  anything not parsable (similarly to `clean_block`)

### Bugfixes


----
## 0.2.0

Moved to `alpha`

Improvements to read more versatile formats

### Improvements

* Tests include a sample-set of gcode files from varying CAM software and authors.
* `lsenv` in deployment script.
* added `GCodeLineNumber` and `GCodeProgramName` (in response to [#5](https://github.com/fragmuffin/pygcode/issues/5)).
* `GCodeCancelCannedCycle` sets machine mode to `None`, and is run first in list of `motion` gcodes.
* Error message for unsupported gcodes is more helpful / relevant.
* Optional whitespace in `Word`, (eg: `X-1.2` and `X -1.2` are now both valid)

### Bugfixes

* [#5](https://github.com/fragmuffin/pygcode/issues/5) Line number in program


----
## 0.1.2

Changes to accommodate implementation of [grbl-stream](https://github.com/fragmuffin/grbl-stream)

### Improvements

- added `NullMachine`, `NullState`, and `NullMode` (not assuming any machine state)
- `Block` length is the number of gcodes + 1 if modal parameters exists

### Bugfixes

- `%` enclosed lines are considered to be _macros_ when parsing
- added axes `ABCXYZ` as valid parameters for `G10` (eg: `G10 L20 X0 Y0 Z0`)
