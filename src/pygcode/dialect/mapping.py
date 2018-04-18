
# ---------------- Registration Decorators ----------------
def gcode_dialect(*names):
    """
    GCode class dialect registration decorator

    :param names: name of relevant dialects
    :type names: :class:`list` of :class:`str` instances

    For example::

        from pygcode.dialect import gcode_dialect as dialect
        from pygcode.gcodes import GCode

        @dialect('linuxcnc')
        class GCodeRapidMove(GCode):
            word_key = Word('G', 0)

            def _process(self, machine):
                params = self.get_param_dict(letters=machine.axes)
                machine.move_to(rapid=True, **params)

        @dialect('reprap')
        clsas GCodeRapidMove2(GCode):  # name changed because scope is the same
            word_key = Word('G', 0)

            def _process(self, machine):
                params = self.get_param_dict(letters=machine.axes)
                params = {k: -v for (k, v) in params.items()}  # negate parameters
                machine.move_to(rapid=True, **params)

    When processing a ``linuxcnc`` dialect, the machine coordintes would be
    positive. Conversely the coordintes would be negated if processed in the
    ``reprap`` dialect.

    """
    # TODO

def word_dialect(*names):
    """

    """

    # TODO


# ---------------- Dialect  ----------------
