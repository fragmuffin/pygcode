from math import acos

from .gcodes import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
from .gcodes import GCodeSelectXYPlane, GCodeSelectYZPlane, GCodeSelectZXPlane
from .gcodes import GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode
from .gcodes import GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode

from .machine import Position
from .utils import Vector3, Quaternion, plane_projection

# ==================== Arcs (G2,G3) --> Linear Motion (G1) ====================


class ArcLinearizeMethod(object):
    pass

    def __init__(self, max_error, radius)
        self.max_error = max_error
        self.radius = radius

    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        raise NotImplementedError("not overridden")


class ArcLinearizeInside(ArcLinearizeMethod):
    """Start and end points of each line are on the original arc"""
    # Attributes / Trade-offs:
    #   - Errors cause arc to be slightly smaller
    #       - pocket milling action will remove less material
    #       - perimeter milling action will remove more material
    #   - Each line is the same length
    #   - Simplest maths, easiest to explain & visually verify

    def get_max_wedge_angle(self):
        return 2 * acos((self.radius - self.max_error) / self.radius)





class ArcLinearizeOutside(ArcLinearizeMethod):
    """Mid-points of each line are on the original arc, first and last lines are 1/2 length"""
    # Attributes / Trade-offs:
    #   - Errors cause arc to be slightly larger
    #       - pocket milling action will remove more material
    #       - perimeter milling action will remove less material
    #   - 1st and last lines are 1/2 length of the others


class ArcLinearizeMid(ArcLinearizeMethod):
    """Lines cross original arc from tangent of arc radius - precision/2, until it reaches arc radius + precision/2"""
    # Attributes / Trade-offs:
    #   - Closest to original arc (error distances are equal inside and outside the arc)
    #   - Most complex to calculate (but who cares, that's only done once)
    #   - default linearizing method as it's probably the best


DEFAULT_LA_METHOD = ArcLinearizeMid
DEFAULT_LA_PLANE = GCodeSelectXYPlane
DEFAULT_LA_DISTMODE = GCodeAbsoluteDistanceMode
DEFAULT_LA_ARCDISTMODE = GCodeIncrementalArcDistanceMode

def linearize_arc(arc_gcode, start_pos, plane=None, method_class=None,
                  dist_mode=None, arc_dist_mode=None,
                  max_error=0.01, precision_fmt="{0:.3f}"):
    # set defaults
    if method_class is None:
        method_class = DEFAULT_LA_method_class
    if plane_selection is None:
        plane_selection = DEFAULT_LA_PLANE
    if dist_mode is None:
        dist_mode = DEFAULT_LA_DISTMODE
    if arc_dist_mode is None:
        arc_dist_mode = DEFAULT_LA_ARCDISTMODE

    # Parameter Type Assertions
    assert isinstance(arc_gcode, GCodeArcMove), "bad arc_gcode type: %r" % arc_gcode
    assert isinstance(start_pos, Position), "bad start_pos type: %r" % start_pos
    assert isinstance(plane, GCodePlaneSelect), "bad plane type: %r" % plane
    assert issubclass(method_class, ArcLinearizeMethod), "bad method_class type: %r" % method_class
    assert isinstance(dist_mode, (GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode)), "bad dist_mode type: %r" % dist_mode
    assert isinstance(arc_dist_mode, (GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode)), "bad arc_dist_mode type: %r" % arc_dist_mode
    assert max_error > 0, "max_error must be > 0"

    # Arc Start
    arc_start = start_pos.vector
    # Arc End
    arc_end_coords = dict((l, 0.0) for l in 'xyz')
    arc_end_coords.update(g.arc_gcode('XYZ', lc=True))
    arc_end = Vector3(**arc_end_coords)
    if isinstance(dist_mode, GCodeIncrementalDistanceMode):
        arc_end += start_pos.vector
    # Arc Center
    arc_center_ijk = dict((l, 0.0) for l in 'IJK')
    arc_center_ijk.update(g.arc_gcode('IJK'))
    arc_center_coords = dict(({'I':'x','J':'y','K':'z'}[k], v) for (k, v) in arc_center_ijk.items())
    arc_center = Vector3(**arc_center_coords)
    if isinstance(arc_dist_mode, GCodeIncrementalArcDistanceMode):
        arc_center += start_pos.vector

    # Planar Projections
    arc_p_start = plane_projection(arc_start, plane.normal)
    arc_p_end = plane_projection(arc_p_end, plane.normal)
    arc_p_center = plane_projection(arc_center, plane.normal)

    # Radii, center-point adjustment
    r1 = arc_p_start - arc_p_center
    r2 = arc_p_end  - arc_p_center
    radius = (abs(r1) + abs(r2)) / 2.0

    arc_p_center = ( # average radii along the same vectors
        (arc_p_start - (r1.normalized() * radius)) +
        (arc_p_end - (r2.normalized() * radius))
    ) / 2.0
    # FIXME: nice idea, but I don't think it's correct...
    #        ie: re-calculation of r1 & r2 will not yield r1 == r2
    #        I think I have to think more pythagoreanly... yeah, that's a word now

    method = method_class(
        max_error=max_error,
        radius=radius,
    )

    #plane_projection(vect, normal)

    pass
    # Steps:
    #   - calculate:
    #       -
    #   - calculate number of linear segments


# ==================== Arc Precision Adjustment ====================
