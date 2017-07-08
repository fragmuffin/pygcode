from .line import Line

#from .machine import AbstractMachine

class GCodeFile(object):
    def __init__(self, filename=None):
        self.filename = filename

        # Initialize
        self.lines = []

    def append(self, line):
        assert isinstance(line, Line), "invalid line type"
        self.lines.append(line)


class GCodeParser(object):
    """Parse a gocde file"""
    def __init__(self, filename):
        self.filename = filename
        self._fh = open(filename, 'r')

    def iterlines(self):
        for line in self._fh.readlines():
            yield Line(line)

    def close(self):
        self._fh.close()
