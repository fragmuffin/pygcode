import re


class CommentBase(object):
    ORDER = 0
    MULTICOMMENT_JOINER = ". " # joiner if multiple comments are found on the same line
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "<{class_name}: '{comment}'>".format(
            class_name=self.__class__.__name__,
            comment=str(self),
        )


class CommentSemicolon(CommentBase):
    "Comments of the format: 'G00 X1 Y2 ; something profound'"
    ORDER = 1
    AUTO_REGEX = re.compile(r'\s*;\s*(?P<text>.*)$')

    def __str__(self):
        return "; {text}".format(text=self.text)


class CommentBrackets(CommentBase):
    "Comments of the format: 'G00 X1 Y2 (something profound)"
    ORDER = 2
    AUTO_REGEX = re.compile(r'\((?P<text>[^\)]*)\)')

    def __str__(self):
        return "({text})".format(text=self.text)


Comment = CommentBrackets # default comment type


def split_line(line_text):
    """
    Split functional block content from comments
    :param line_text: line from gcode file
    :return: tuple of (str(<functional block code>), CommentBase(<comment(s)>))
    """
    comments_class = None

    # Auto-detect comment type if I can
    comments = []
    block_str = line_text.rstrip("\n") # to remove potential return carriage from comment body

    for cls in sorted(CommentBase.__subclasses__(), key=lambda c: c.ORDER):
        matches = list(cls.AUTO_REGEX.finditer(block_str))
        if matches:
            for match in reversed(matches):
                # Build list of comment text
                comments.insert(0, match.group('text'))  # prepend
                # Remove comments from given block_str
                block_str = block_str[:match.start()] + block_str[match.end():]
            comments_class = cls
            break

    # Create comment instance if content was found
    comment_obj = None
    if comments_class:
        comment_text = comments_class.MULTICOMMENT_JOINER.join(comments)
        comment_obj = comments_class(comment_text)

    return (block_str, comment_obj)
