

class MachineState(object):
    def __init__(self, axes=('x', 'y', 'z')):
        self.axes = axes

        # initialize
        self.position = {}
        for axis in self.axes:
            self.position[axis] = 0

        self.time = 0



class AbstractMachine(object):
    """Basis for a real / virtualized machine to process gcode"""
    def __init__(self, *args, **kwargs):
        self.axes = kwargs.get('axes', ('x', 'y', 'z'))
        self.max_rate = kwargs.get('max_rate', {
            'x': 500, # mm/min
            'y': 500, # mm/min
            'z': 500, # mm/min
        })
        self.max_travel = kwargs.get('max_travel', {
            'x': 200, # mm
            'y': 200, # mm
            'z': 200, # mm
        })
        self.max_spindle_speed = kwargs.get('max_spindle_speed', 1000) # rpm
        self.min_spindle_speed = kwargs.get('max_spindle_speed', 0) # rpm

        # initialize
        self.state = MachineState(self.axes)

        # machine-specific initialization
        self.machine_init(*args, **kwargs)

    def machine_init(self, *args, **kwargs):
        # Executed last in instances' __init__ call.
        # Parameters are identical to that of __init__
        pass

    def process_line(self, line):
        """Change machine's state based on the given gcode line"""
        pass # TODO




"""
class Axes(object):
    pass

class MyMachineState(MachineState):
    axes_state_class = AxesState
    pass

class MyMachine(AbstractMachine):
    available_axes = set('xyz')
    state_class = MyMachineState


m = MyMachine(
    state=MyMachineState(
        absolute_position=
    ),
)

"""
