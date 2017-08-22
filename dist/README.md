# Change History

## 0.2.0

Moved to `alpha`

Improvements to read more versatile formats

### Improvements

* Tests include a sample-set of gcode files from varying CAM software and authors.
* `lsenv` in deployment script.
* added `GCodeLineNumber` and `GCodeProgramName` (in response to #5).
* `GCodeCancelCannedCycle` sets machine mode to `None`, and is run first in list of `motion` gcodes.
* Error message for unsupported gcodes is more helpful / relevant.
* Optional whitespace in `Word`, (eg: `X-1.2` and `X -1.2` are now both valid)

### Bugfixes

* Line number in program (#5)


## 0.1.2

Changes to accommodate implementation of [grbl-stream](https://github.com/fragmuffin/grbl-stream)

### Improvements

- added `NullMachine`, `NullState`, and `NullMode` (not assuming any machine state)
- `Block` length is the number of gcodes + 1 if modal parameters exists

### Bugfixes

- `%` enclosed lines are considered to be _macros_ when parsing
- added axes `ABCXYZ` as valid parameters for `G10` (eg: `G10 L20 X0 Y0 Z0`)
