from .comment import split_line
from .block import Block

class Line(object):
    def __init__(self, text=None):
        self._text = text

        # Initialize
        self.block = None
        self.comment = None

        # Split line into block text, and comments
        if text is not None:
            (block_str, comment) = split_line(text)
            if block_str:
                self.block = Block(block_str)
            if comment:
                self.comment = comment

    @property
    def text(self):
        if self._text is None:
            return self.build_line_text()
        return self._text


    def build_line_text(self):
        return ' '.join([str(x) for x in [self.block, self.comment] if x]) + '\n'
