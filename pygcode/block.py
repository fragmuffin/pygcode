import re
from .words import iter_words, WORD_MAP
from .gcodes import words_to_gcodes

class Block(object):
    """GCode block (effectively any gcode file line that defines any <word><value>)"""

    def __init__(self, text):
        """
        Block Constructor
        :param A-Z: gcode parameter values
        :param comment: comment text
        """

        self._raw_text = text  # unaltered block content (before alteration)

        # clean up block string
        text = re.sub(r'(^\s+|\s+$)', '', text) # remove whitespace padding
        text = re.sub(r'\s+', ' ', text) # remove duplicate whitespace with ' '

        self.text = text

        self.words = list(iter_words(self.text))
        #self.gcodes = list(words_to_gcodes(self.words))

    def __getattr__(self, k):
        if k in WORD_MAP:
            for w in self.words:
                if w.letter == k:
                    return w
            # if word is not in this block:
            return None

        else:
            raise AttributeError("'{cls}' object has no attribute '{key}'".format(
                cls=self.__class__.__name__,
                key=k
            ))
