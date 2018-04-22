
# Data Classes

class WordType(object):
    def __init__(self, cls, value_regex, description, clean_value):
        self.cls = cls
        self.value_regex = value_regex
        self.description = description
        self.clean_value = clean_value
