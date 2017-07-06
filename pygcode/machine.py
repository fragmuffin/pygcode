
from collections import defaultdict

from .gcodes import MODAL_GROUP_MAP, GCode
from .line import Line

from .machinestate import MachineState


class Machine(object):
    def __init__(self):
        self.state = MachineState()

    def process(self, *gcode_list, **kwargs):
        """
        Process gcodes
        :param gcode_list: list of GCode instances
        :param modal_params: list of Word instances to be applied to current movement mode
        """
        modal_params = kwargs.get('modal_params', [])
        for gcode in sorted(gcode_list):
            self.state.set_mode(gcode)  # if gcode is not modal, it's ignored

            # TODO: gcode instance to change machine's state
