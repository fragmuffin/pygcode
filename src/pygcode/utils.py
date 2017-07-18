import sys
from copy import copy, deepcopy

from euclid3 import Vector3, Quaternion


# ==================== Geometric Utilities ====================
def quat2align(to_align, with_this, normalize=True):
    """
    Calculate Quaternion that will rotate a given vector to align with another
    can accumulate with perpendicular alignemnt vectors like so:
        (x_axis, z_axis) = (Vector3(1, 0, 0), Vector3(0, 0, 1))
        q1 = quat2align(v1, z_axis)
        q2 = quat2align(q1 * v2, x_axis)
        # assuming v1 is perpendicular to v2
        q3 = q2 * q1  # application of q3 to any vector will re-orient it to the
                      # coordinate system defined by (v1,v2), as (z,x) respectively.
    :param to_align: Vector3 instance to be rotated
    :param with_this: Vector3 instance as target for alignment
    :result: Quaternion such that: q * to_align == with_this
    """
    # Normalize Vectors
    if normalize:
        to_align = to_align.normalized()
        with_this = with_this.normalized()
    # Calculate Quaternion
    return Quaternion.new_rotate_axis(
        angle=to_align.angle(with_this),
        axis=to_align.cross(with_this),
    )


def quat2coord_system(origin1, origin2, align1, align2):
    """
    Calculate Quaternion to apply to any vector to re-orientate it to another
    (target) coordinate system.
    (note: both origin and align coordinate systems must use right-hand-rule)
    :param origin1: origin(1|2) are perpendicular vectors in the original coordinate system
    :param origin2: see origin1
    :param align1: align(1|2) are 2 perpendicular vectors in the target coordinate system
    :param align2: see align1
    :return: Quaternion such that q * origin1 = align1, and q * origin2 = align2
    """
    # Normalize Vectors
    origin1 = origin1.normalized()
    origin2 = origin2.normalized()
    align1 = align1.normalized()
    align2 = align2.normalized()
    # Calculate Quaternion
    q1 = quat2align(origin1, align1, normalize=False)
    q2 = quat2align(q1 * origin2, align2, normalize=False)
    return q2 * q1


def plane_projection(vect, normal):
    """
    Project vect to a plane represented by normal
    :param vect: vector to be projected (Vector3)
    :param normal: normal of plane to project on to (Vector3)
    :return: vect projected onto plane represented by normal
    """
    # ref: https://en.wikipedia.org/wiki/Vector_projection
    n = normal.normalized()
    return vect - (n * vect.dot(n))


# ==================== GCode Utilities ====================
def omit_redundant_modes(gcode_iter):
    """
    Replace redundant machine motion modes with whitespace,
    :param gcode_iter: iterable to return with modifications
    """

    from .machine import Machine, Mode
    from .gcodes import MODAL_GROUP_MAP
    class NullModeMachine(Machine):
        MODE_CLASS = type('NullMode', (Mode,), {'default_mode': ''})
    m = NullModeMachine()

    for g in gcode_iter:
        if (g.modal_group is not None) and (m.mode.modal_groups[g.modal_group] is not None):
            # g-code has a modal groups, and the machine's mode
            # (of the same modal group) is not None
            if m.mode.modal_groups[g.modal_group].word == g.word:
                # machine's mode & g-code's mode match (no machine change)
                if g.modal_group == MODAL_GROUP_MAP['motion']:
                    # finally: g-code sets a motion mode in the machine
                    g = copy(g) # duplicate gcode object
                    # stop redundant g-code word from being printed
                    g._whitespace_prefix = True

        m.process_gcodes(g)
        yield g
