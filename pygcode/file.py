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


def parse(filename):
    # FIXME: should be an iterator, and also not terrible
    file = GCodeFile()
    with open(filename, 'r') as fh:
        for line in fh.readlines():
            line_obj = Line(line)
            # FIXME: don't dump entire file into RAM; change to generator model
            file.append(line_obj)
    return file
