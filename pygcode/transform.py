from math import cos, acos, atan2, pi, sqrt, ceil

from .gcodes import GCodeLinearMove
from .gcodes import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
from .gcodes import GCodePlaneSelect, GCodeSelectXYPlane, GCodeSelectYZPlane, GCodeSelectZXPlane
from .gcodes import GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode
from .gcodes import GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode

from .machine import Position
from .exceptions import GCodeParameterError
from .utils import Vector3, Quaternion, plane_projection


# ==================== Arcs (G2,G3) --> Linear Motion (G1) ====================

class ArcLinearizeMethod(object):
    def __init__(self, max_error, plane_normal,
                 arc_p_start, arc_p_end, arc_p_center,
                 arc_radius, arc_angle, helical_start, helical_end):
        self.max_error = max_error
        self.plane_normal = plane_normal
        self.arc_p_start = arc_p_start
        self.arc_p_end = arc_p_end
        self.arc_p_center = arc_p_center
        self.arc_radius = arc_radius
        self.arc_angle = arc_angle
        self.helical_start = helical_start
        self.helical_end = helical_end

        if self.max_error > self.arc_radius:
            self.max_error = self.arc_radius

    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        raise NotImplementedError("not overridden")

    def iter_vertices(self):
        """Yield absolute (<start vertex>, <end vertex>) for each line for the arc"""
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
        return abs(2 * acos((self.arc_radius - self.max_error) / self.arc_radius))

    def iter_vertices(self):
        wedge_count = int(ceil(abs(self.arc_angle) / self.get_max_wedge_angle()))
        wedge_angle = self.arc_angle / wedge_count
        start_radius = self.arc_p_start - self.arc_p_center
        helical_delta = (self.helical_end - self.helical_start) / wedge_count

        l_p_start = self.arc_p_start
        l_start = l_p_start + self.helical_start
        for i in range(wedge_count):
            q_end = Quaternion.new_rotate_axis(
                angle=wedge_angle * (i+1),
                axis=-self.plane_normal,
            )
            # Projected on selected plane
            l_p_end = (q_end * start_radius)  + self.arc_p_center
            # Helical displacement
            l_end = l_p_end + (self.helical_start + (helical_delta * (i+1)))

            yield (l_start, l_end)

            # start of next line is the end of this one
            l_start = l_end


class ArcLinearizeOutside(ArcLinearizeMethod):
    """Mid-points of each line are on the original arc, first and last lines are 1/2 length"""
    # Attributes / Trade-offs:
    #   - Errors cause arc to be slightly larger
    #       - pocket milling action will remove more material
    #       - perimeter milling action will remove less material
    #   - 1st and last lines are 1/2 length of the others

    def get_max_wedge_angle(self):
        return abs(2 * acos(self.arc_radius / (self.arc_radius + self.max_error)))

    def iter_vertices(self):
        # n wedges distributed like:
        #   - 1/2 wedge : first line
        #   - n-1 wedges : outer perimeter
        #   - last 1/2 wedge : last line
        wedge_count = int(ceil(abs(self.arc_angle) / self.get_max_wedge_angle()))
        wedge_angle = self.arc_angle / wedge_count
        start_radius = self.arc_p_start - self.arc_p_center
        # radius of outer circle (across which the linear lines will span)
        error_radius = start_radius.normalized() * (self.arc_radius / cos(wedge_angle / 2))

        l_p_start = start_radius + self.arc_p_center
        l_start = l_p_start + self.helical_start
        for i in range(wedge_count):
            cur_angle = (wedge_angle * i) + (wedge_angle / 2)
            q_end = Quaternion.new_rotate_axis(angle=cur_angle, axis=-self.plane_normal)

            # Projected on selected plane
            l_p_end = (q_end * error_radius)  + self.arc_p_center
            # Helical displacement
            l_end = l_p_end + self.helical_start + ((self.helical_end - self.helical_start) * (cur_angle / self.arc_angle))

            yield (l_start, l_end)

            # start of next line is the end of this one
            l_start = l_end

        yield (l_start, self.arc_p_end + self.helical_end)


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
                  max_error=0.01, decimal_places=3):
    # set defaults
    if method_class is None:
        method_class = DEFAULT_LA_method_class
    if plane is None:
        plane = DEFAULT_LA_PLANE()
    if dist_mode is None:
        dist_mode = DEFAULT_LA_DISTMODE()
    if arc_dist_mode is None:
        arc_dist_mode = DEFAULT_LA_ARCDISTMODE()

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
    arc_end_coords = dict(zip('xyz', arc_start.xyz))
    arc_end_coords.update(arc_gcode.get_param_dict('XYZ', lc=True))
    arc_end = Vector3(**arc_end_coords)
    if isinstance(dist_mode, GCodeIncrementalDistanceMode):
        arc_end += start_pos.vector

    # Planar Projections
    arc_p_start = plane_projection(arc_start, plane.normal)
    arc_p_end = plane_projection(arc_end, plane.normal)

    # Arc radius, calcualted one of 2 ways:
    #   - R: arc radius is provided
    #   - IJK: arc's center-point is given, errors mitigated
    arc_gcode.assert_params()
    if 'R' in arc_gcode.params:
        # R: radius magnitude specified
        if abs(arc_p_start - arc_p_end) < max_error:
            raise GCodeParameterError(
                "arc starts and finishes in the same spot; cannot "
                "speculate where circle's center is: %r" % arc_gcode
            )

        arc_radius = abs(arc_gcode.R)  # arc radius (magnitude)

    else:
        # IJK: radius vertex specified
        arc_center_ijk = dict((l, 0.) for l in 'IJK')
        arc_center_ijk.update(arc_gcode.get_param_dict('IJK'))
        arc_center_coords = dict(({'I':'x','J':'y','K':'z'}[k], v) for (k, v) in arc_center_ijk.items())
        arc_center = Vector3(**arc_center_coords)
        if isinstance(arc_dist_mode, GCodeIncrementalArcDistanceMode):
            arc_center += start_pos.vector

        # planar projection
        arc_p_center = plane_projection(arc_center, plane.normal)

        # Radii
        r1 = arc_p_start - arc_p_center
        r2 = arc_p_end  - arc_p_center

        # average the 2 radii to get the most accurate radius
        arc_radius = (abs(r1) + abs(r2)) / 2.

    # Find Circle's Center (given radius)
    arc_span = arc_p_end - arc_p_start  # vector spanning from start -> end
    arc_span_mid = arc_span * 0.5  # arc_span's midpoint
    if arc_radius < abs(arc_span_mid):
        raise GCodeParameterError("circle cannot reach endpoint at this radius: %r" % arc_gcode)
    # vector from arc_span midpoint -> circle's centre
    radius_mid_vect = arc_span_mid.normalized().cross(plane.normal) * sqrt(arc_radius**2 - abs(arc_span_mid)**2)

    if 'R' in arc_gcode.params:
        # R: radius magnitude specified
        if isinstance(arc_gcode, GCodeArcMoveCW) == (arc_gcode.R < 0):
            arc_p_center = arc_p_start + arc_span_mid - radius_mid_vect
        else:
            arc_p_center = arc_p_start + arc_span_mid + radius_mid_vect
    else:
        # IJK: radius vertex specified
        # arc_p_center is defined as per IJK params, this is an adjustment
        arc_p_center_options = [
            arc_p_start + arc_span_mid - radius_mid_vect,
            arc_p_start + arc_span_mid + radius_mid_vect
        ]
        if abs(arc_p_center_options[0] - arc_p_center) < abs(arc_p_center_options[1] - arc_p_center):
            arc_p_center = arc_p_center_options[0]
        else:
            arc_p_center = arc_p_center_options[1]

    # Arc's angle (first rotated back to xy plane)
    xy_c2start = plane.quat * (arc_p_start - arc_p_center)
    xy_c2end = plane.quat * (arc_p_end - arc_p_center)
    (a1, a2) = (atan2(*xy_c2start.yx), atan2(*xy_c2end.yx))
    if isinstance(arc_gcode, GCodeArcMoveCW):
        arc_angle = (a1 - a2) % (2 * pi)
    else:
        arc_angle = -((a2 - a1) % (2 * pi))

    # Helical interpolation
    helical_start = plane.normal * arc_start.dot(plane.normal)
    helical_end = plane.normal * arc_end.dot(plane.normal)

    # Parameters determined above:
    #   - arc_p_start   arc start point
    #   - arc_p_end     arc end point
    #   - arc_p_center  arc center
    #   - arc_angle     angle between start & end (>0 is ccw, <0 is cw) (radians)
    #   - helical_start distance along plane.normal of arc start
    #   - helical_disp  distance along plane.normal of arc end

    #print((
    #    "linearize_arc params\n"
    #    "   - arc_p_start   {arc_p_start}\n"
    #    "   - arc_p_end     {arc_p_end}\n"
    #    "   - arc_p_center  {arc_p_center}\n"
    #    "   - arc_radius    {arc_radius}\n"
    #    "   - arc_angle     {arc_angle:.4f} ({arc_angle_deg:.3f} deg)\n"
    #    "   - helical_start {helical_start}\n"
    #    "   - helical_end   {helical_end}\n"
    #).format(
    #    arc_p_start=arc_p_start,
    #    arc_p_end=arc_p_end,
    #    arc_p_center=arc_p_center,
    #    arc_radius=arc_radius,
    #    arc_angle=arc_angle, arc_angle_deg=arc_angle * (180/pi),
    #    helical_start=helical_start,
    #    helical_end=helical_end,
    #))

    method_class_params = {
        'max_error': max_error,
        'plane_normal': plane.normal,
        'arc_p_start': arc_p_start,
        'arc_p_end': arc_p_end,
        'arc_p_center': arc_p_center,
        'arc_radius': arc_radius,
        'arc_angle': arc_angle,
        'helical_start': helical_start,
        'helical_end': helical_end,
    }
    method = method_class(**method_class_params)

    # Iterate & yield each linear line (start, end) vertices
    if isinstance(dist_mode, GCodeAbsoluteDistanceMode):
        # Absolute coordinates
        for line_vertices in method.iter_vertices():
            (l_start, l_end) = line_vertices
            yield GCodeLinearMove(**dict(zip('XYZ', l_end.xyz)))
    else:
        # Incremental coordinates (beware cumulative errors)
        cur_pos = arc_start
        for line_vertices in method.iter_vertices():
            (l_start, l_end) = line_vertices
            l_delta = l_end - cur_pos

            # round delta coordinates (introduces errors)
            for axis in 'xyz':
                setattr(l_delta, axis, round(getattr(l_delta, axis), decimal_places))
            yield GCodeLinearMove(**dict(zip('XYZ', l_delta.xyz)))
            cur_pos += l_delta # mitigate errors by also adding them the accumulated cur_pos


# ==================== Arc Precision Adjustment ====================
