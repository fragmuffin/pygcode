# Change History

## 0.1.2

Changes to accommodate implementation of [grbl-stream](https://github.com/fragmuffin/grbl-stream)

### Improvements

- added `NullMachine`, `NullState`, and `NullMode` (not assuming any machine state)
- `Block` length is the number of gcodes + 1 if modal parameters exists

### Bugfixes

- `%` enclosed lines are considered to be _macros_ when parsing
- added axes `ABCXYZ` as valid parameters for `G10` (eg: `G10 L20 X0 Y0 Z0`)
