__all__ = [

    'DEFAULT',

    # registration decorators
    'gcode_dialect',
    'word_dialect',
]

DEFAULT = 'linuxcnc'

# Registration decorators
from .mapping import gcode_dialect
from .mapping import word_dialect
