import re
from .words import text2words, WORD_MAP
from .gcodes import words2gcodes

class Block(object):
    """GCode block (effectively any gcode file line that defines any <word><value>)"""

    def __init__(self, text=None, verify=True):
        """
        Block Constructor
        :param A-Z: gcode parameter values
        :param comment: comment text
        """

        self._raw_text = None
        self._text = None
        self.words = []
        self.gcodes = []
        self.modal_params = []

        # clean up block string
        if text:
            self._raw_text = text  # unaltered block content (before alteration)
            text = re.sub(r'(^\s+|\s+$)', '', text) # remove whitespace padding
            text = re.sub(r'\s+', ' ', text) # remove duplicate whitespace with ' '
            self._text = text  # cleaned up block content

            # Get words from text, and group into gcodes
            self.words = list(text2words(self._text))
            (self.gcodes, self.modal_params) = words2gcodes(self.words)

            # Verification
            if verify:
                self._assert_gcodes()

    @property
    def text(self):
        if self._text:
            return self._text
        return str(self)

    def _assert_gcodes(self):
        modal_groups = set()
        code_words = set()

        for gc in self.gcodes:

            # Assert all gcodes are not repeated in the same block
            if gc.word in code_words:
                raise AssertionError("%s cannot be in the same block" % ([
                    x for x in self.gcodes
                    if x.modal_group == gc.modal_group
                ]))
            code_words.add(gc.word)

            # Assert all gcodes are from different modal groups
            if gc.modal_group is not None:
                if gc.modal_group in modal_groups:
                    raise AssertionError("%s cannot be in the same block" % ([
                        x for x in self.gcodes
                        if x.modal_group == gc.modal_group
                    ]))
                modal_groups.add(gc.modal_group)

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

    def __bool__(self):
        return bool(self.words)

    __nonzero__ = __bool__  # python < 3 compatability

    def __str__(self):
        return ' '.join(str(x) for x in (self.gcodes + self.modal_params))
