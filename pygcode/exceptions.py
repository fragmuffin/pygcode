
# ===================== Parsing Exceptions =====================
class GCodeBlockFormatError(Exception):
    """Raised when errors encountered while parsing block text"""

class GCodeParameterError(Exception):
    """Raised for conflicting / invalid / badly formed parameters"""

class GCodeWordStrError(Exception):
    """Raised when issues found while parsing a word string"""

# ===================== Machine Exceptions =====================
class MachineInvalidAxis(Exception):
    """Raised if an axis is invalid"""
    # For example: for axes X/Y/Z, set the value of "Q"; wtf?

class MachineInvalidState(Exception):
    """Raised if a machine state is set incorrectly, or in conflict"""
