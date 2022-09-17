=======
pygcode
=======

GCODE Parser for Python

Currently in development, ``pygcode`` is a low-level GCode interpreter
for python.


Changes made
============
This fork allows the user to pass a parameter to a Word Object that will truncate the x and y floats
for increased precision. Scientific notation is also not allowed to be output due to the CNC Machine
not being able to handle it and the dependencies are pinned to prevent future issues.


Installation
============

Install using ``pip``

``pip install pygcode``

or `download directly from PyPi <https://pypi.python.org/pypi/pygcode>`__


Documentation
=============

`Check out the wiki <https://github.com/fragmuffin/pygcode/wiki>`__ for documentation.

