import re
import itertools
import six

from . import dialects
from .exceptions import GCodeBlockFormatError, GCodeWordStrError

class Word(object):
    def __init__(self, *args, **kwargs):
        # Parameters (listed)
        args_count = len(args)
        if args_count == 1:
            # Word('G90')
            letter = args[0][0] # first letter
            value = args[0][1:] # rest of string
        elif args_count == 2:
            # Word('G', 90)
            (letter, value) = args
        else:
            raise AssertionError("input arguments either: (letter, value) or (word_str)")

        # Parameters (keyword)
        dialect = kwargs.pop('dialect', dialects.get_default())

        letter = letter.upper()

        self._word_map = getattr(getattr(dialects, dialect), 'WORD_MAP')
        self._value_class = self._word_map[letter].cls
        self._value_clean = self._word_map[letter].clean_value

        self.letter = letter
        self.value = value

    def __str__(self):
        return "{letter}{value}".format(
            letter=self.letter,
            value=self.value_str,
        )

    def __repr__(self):
        return "<{class_name}: {string}>".format(
            class_name=self.__class__.__name__,
            string=str(self),
        )

    # Sorting
    def __lt__(self, other):
        return (self.letter, self.value) < (other.letter, other.value)

    def __gt__(self, other):
        return (self.letter, self.value) > (other.letter, other.value)

    def __le__(self, other):
        return (self.letter, self.value) <= (other.letter, other.value)

    def __ge__(self, other):
        return (self.letter, self.value) >= (other.letter, other.value)

    # Equality
    def __eq__(self, other):
        if isinstance(other, six.string_types):
            other = str2word(other)
        return (self.letter == other.letter) and (self.value == other.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    # Hashing
    def __hash__(self):
        return hash((self.letter, self.value))

    @property
    def value_str(self):
        """Clean string representation, for consistent file output"""
        return self._value_clean(self.value)

    # Value Properties
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = self._value_class(new_value)

    @property
    def description(self):
        return "%s: %s" % (self.letter, self._word_map[self.letter].description)


def text2words(block_text, dialect=None):
    """
    Iterate through block text yielding Word instances
    :param block_text: text for given block with comments removed
    """
    if dialect is None:
        dialect = dialects.get_default()
    word_map = getattr(getattr(dialects, dialect), 'WORD_MAP')

    next_word = re.compile(r'^.*?(?P<letter>[%s])' % ''.join(word_map.keys()), re.IGNORECASE)

    index = 0
    while True:
        letter_match = next_word.search(block_text[index:])
        if letter_match:
            # Letter
            letter = letter_match.group('letter').upper()
            index += letter_match.end() # propogate index to start of value

            # Value
            value_regex = word_map[letter].value_regex
            value_match = value_regex.search(block_text[index:])
            if value_match is None:
                raise GCodeWordStrError("word '%s' value invalid" % letter)
            value = value_match.group() # matched text

            yield Word(letter, value)

            index += value_match.end() # propogate index to end of value
        else:
            break

    remainder = block_text[index:]
    if remainder and re.search(r'\S', remainder):
        raise GCodeWordStrError("block code remaining '%s'" % remainder)


def str2word(word_str):
    words = list(text2words(word_str))
    if words:
        if len(words) > 1:
            raise GCodeWordStrError("more than one word given")
        return words[0]
    return None


def words2dict(word_list, limit_word_letters=None):
    """
    Represent a list of words as a dict
    :param limit_word_letters: iterable containing a white-list of word letters (None allows all)
    :return: dict of the form: {<letter>: <value>, ... }
    """
    # Remember: duplicate word letters cannot be represented as a dict
    return dict(
        (w.letter, w.value) for w in word_list
        if (limit_word_letters is None) or (w.letter in limit_word_letters)
    )
