import re

from .comment import split_line
from .block import Block

class Line(object):

    line_regex = re.compile(r'^(?P<block_and_comment>.*?)?(?P<macro>%.*%?)?\s*$')

    def __init__(self, text=None):
        self._text = text

        # Initialize
        self.block = None
        self.comment = None
        self.macro = None

        # Split line into block text, and comments
        if text is not None:
            match = self.line_regex.search(text)

            block_and_comment = match.group('block_and_comment')
            self.macro = match.group('macro')

            (block_str, comment) = split_line(block_and_comment)
            self.block = Block(block_str)
            if comment:
                self.comment = comment

    @property
    def text(self):
        if self._text is None:
            return str(self)
        return self._text

    @property
    def gcodes(self):
        """self.block.gcodes passthrough"""
        return self.block.gcodes

    def __str__(self):
        return ' '.join([str(x) for x in [self.block, self.comment, self.macro] if x])
