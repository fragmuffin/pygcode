import re
from .words import iter_words, WORD_MAP
from .gcodes import words2gcodes

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
        (self.gcodes, self.modal_params) = words2gcodes(self.words)

        self._assert_gcodes()

        # TODO: gcode verification
        #   - gcodes in the same modal_group raises exception

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

    def __str__(self):
        return ' '.join(str(x) for x in (self.gcodes + [p.clean_str for p in self.modal_params]))
