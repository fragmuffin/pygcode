import os
import inspect
import re
import glob
import unittest

# Add relative pygcode to path
from testutils import add_pygcode_to_path, str_lines
add_pygcode_to_path()

# Units under test
from pygcode.machine import Position, Machine
from pygcode.line import Line
from pygcode.exceptions import MachineInvalidAxis
from pygcode.gcodes import (
    GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode,
    GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode,
    GCodeCannedCycleReturnPrevLevel, GCodeCannedCycleReturnToR,
)

# Local paths
_this_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
_test_files_dir = os.path.join(_this_path, 'test-files')

class FileParsingTest(unittest.TestCase):
    filename = os.path.join(_test_files_dir, 'linuxcnc', 'random-sample-1.gcode')

    def test_file(self):
        m = Machine()
        with open(self.filename, 'r') as fh:
            for line_str in fh.readlines():
                line = Line(line_str)
                m.process_block(line.block)


# Get list of test files
_filetype_regex = re.compile(r'\.(tap|nc|ngc|gcode)$', re.IGNORECASE)
_test_files = set()
for dialect in ['linuxcnc']:  # FIXME: get list of all dialects
    for filename in glob.glob(os.path.join(_test_files_dir, dialect, '*')):
        if _filetype_regex.search(filename):
            _test_files.add(filename)

# remove default test file:
_test_files.discard(FileParsingTest.filename)

# Create inheriting class for each gcode file in the _test_files_dir directory
for (i, filename) in enumerate(sorted(_test_files)):
    basename = os.path.basename(filename)
    class_name = "FileParsingTest_" + re.sub(r"""[^a-zA-Z0-9]""", '_', basename)
    globals()[class_name] = type(class_name, (FileParsingTest,), {
        'filename': filename,
    })
