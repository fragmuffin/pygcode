pygcode
=======

GCODE Parser for Python

Currently in development, this is planned to be a pythonic interpreter
and encoder for g-code. I'll be learning along the way, but the plan is
to follow the lead of `GRBL <https://github.com/gnea/grbl>`__.

Installation
------------

``pip install pygcode``

FIXME: well, that's the plan... give me some time to get it going
though.

Usage
-----

Just brainstorming here...

::

    import pygcode
    import math
    import euclid

    gfile_in = pygcode.parse('part1.gcode') #
    gfile_out = pygcode.GCodeFile('part2.gcode')

    total_travel = 0
    total_time = 0

    machine = pygcode.Machine()

    for line in gfile_in.iterlines():

        block = line.block
        if block is None:
            continue

        # validation
        if isinstance(block, pygcode.GCodeArc):
            error = block.r2 - block.r1
            if error > 0.0005:
                raise pygcode.GCodeValidationError("arc points are not on the same circle")
                #block.set_precision(0.0005, method=pygcode.GCodeArc.EFFECT_ENDPOINT)
                block.set_precision(0.0005, method=pygcode.GCodeArc.EFFECT_RADIUS)

        # random metrics
        travel_vector = block.position - machine.state.position # euclid.Vector3 instance
        distance = travel_vector.magnitude()
        travel = block.travel_distance(position=machine.state.position) # eg: distance != travel for G02 & G03

        total_travel += travel
        #total_time += block.time(feed_rate=machine.state.feed_rate) # doesn't consider the feedrate being changed in this block
        total_time += block.time(state=machine.state)

        # rotate : entire file 90deg CCW
        block.rotate(euclid.Quaternion.new_rotate_axis(
            math.pi / 2, euclid.Vector3(0, 0, 1)
        ))
        # translate : entire file x += 1, y += 2 mm (after rotation)
        block.translate(euclid.Vector3(1, 2, 0), unit=pygcode.UNIT_MM)



        # TODO: then do something like write it to another file
        gfile_out.write(block)

    gfile_in.close()
    gfile_out.close()

Supported G-Codes
-----------------

GCode support is planned to follow that of
`GRBL <https://github.com/gnea/grbl>`__ which follows
`LinuxCNC <http://linuxcnc.org>`__ (list of gcodes documented
`here <http://linuxcnc.org/docs/html/gcode.html>`__).

But anything pre v1.0 will be a sub-set, focusing on the issues I'm
having... I'm selfish that way.

TBD: list of gcodes (also as a TODO list)
