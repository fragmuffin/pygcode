from math import sin, cos, tan, asin, acos, atan2, pi, sqrt, ceil

from .gcodes import GCodeLinearMove, GCodeRapidMove
from .gcodes import GCodeArcMove, GCodeArcMoveCW, GCodeArcMoveCCW
from .gcodes import GCodePlaneSelect, GCodeSelectXYPlane, GCodeSelectYZPlane, GCodeSelectZXPlane
from .gcodes import GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode
from .gcodes import GCodeAbsoluteArcDistanceMode, GCodeIncrementalArcDistanceMode
from .gcodes import GCodeCannedCycle
from .gcodes import GCodeDrillingCyclePeck, GCodeDrillingCycleDwell, GCodeDrillingCycleChipBreaking
from .gcodes import GCodeCannedReturnMode, GCodeCannedCycleReturnLevel, GCodeCannedCycleReturnToR
from .gcodes import _gcodes_abs2rel

from .machine import Position
from .exceptions import GCodeParameterError
from .utils import Vector3, Quaternion, plane_projection


# ==================== Arcs (G2,G3) --> Linear Motion (G1) ====================

class ArcLinearizeMethod(object):
    # Chord Phase Offest:
    #   False : each line will span an equal portion of the arc
    #   True  : the first & last chord will span 1/2 the angular distance of all other chords
    chord_phase_offset = False

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

        # Initializing
        self._max_wedge_angle = None
        self._wedge_count = None
        self._wedge_angle = None
        self._inner_radius = None
        self._outer_radius = None

    # Overridden Functions
    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        raise NotImplementedError("not overridden")

    def get_inner_radius(self):
        """Radius each line is tangential to"""
        # IMPORTANT: when overriding, calculate this using self.wedge_angle,
        # (self.wedge_angle will almost always be < self.max_wedge_angle)
        raise NotImplementedError("not overridden")

    def get_outer_radius(self):
        """Radius from which each line forms a chord"""
        # IMPORTANT: when overriding, calculate this using self.wedge_angle,
        # (self.wedge_angle will almost always be < self.max_wedge_angle)
        raise NotImplementedError("not overridden")

    # Properties
    @property
    def max_wedge_angle(self):
        if self._max_wedge_angle is None:
            self._max_wedge_angle = self.get_max_wedge_angle()
        return self._max_wedge_angle

    @property
    def wedge_count(self):
        """
        Number of full wedges covered across the arc.
        NB: if there is phase offset, then the actual number of linearized lines
            is this + 1, because the first and last are considered to be the
            same 'wedge'.
        """
        if self._wedge_count is None:
            self._wedge_count = int(ceil(abs(self.arc_angle) / self.max_wedge_angle))
        return self._wedge_count

    @property
    def wedge_angle(self):
        """Angle each major chord stretches across the original arc"""
        if self._wedge_angle is None:
            self._wedge_angle = self.arc_angle / self.wedge_count
        return self._wedge_angle

    @property
    def inner_radius(self):
        if self._inner_radius is None:
            self._inner_radius = self.get_inner_radius()
        return self._inner_radius

    @property
    def outer_radius(self):
        if self._outer_radius is None:
            self._outer_radius = self.get_outer_radius()
        return self._outer_radius

    # Vertex Generator
    def iter_vertices(self):
        """Yield absolute (<start vertex>, <end vertex>) for each line for the arc"""
        start_vertex = self.arc_p_start - self.arc_p_center
        outer_vertex = start_vertex.normalized() * self.outer_radius
        d_helical = self.helical_end - self.helical_start

        l_p_start = self.arc_p_center + start_vertex
        l_start = l_p_start + self.helical_start

        for i in range(self.wedge_count):
            wedge_number = i + 1
            # Current angle
            cur_angle = self.wedge_angle * wedge_number
            if self.chord_phase_offset:
                cur_angle -= self.wedge_angle / 2.
            elif wedge_number >= self.wedge_count:
                break  # stop 1 iteration short
                # alow last arc to simply span across:
                # <the end of the last line> -> <circle's end point>

            # Next end point as projected on selected plane
            q_end = Quaternion.new_rotate_axis(angle=cur_angle, axis=-self.plane_normal)
            l_p_end = (q_end * outer_vertex) + self.arc_p_center
            # += helical displacement (difference along plane's normal)
            helical_displacement = self.helical_start + (d_helical * (cur_angle / self.arc_angle))
            l_end = l_p_end + helical_displacement

            yield (l_start, l_end)

            # start of next line is the end of this one
            l_start = l_end

        # Last line always ends at the circle's end
        yield (l_start, self.arc_p_end + self.helical_end)


class ArcLinearizeInside(ArcLinearizeMethod):
    """Start and end points of each line are on the original arc"""
    # Attributes / Trade-offs:
    #   - Errors cause arc to be slightly smaller
    #       - pocket milling action will remove less material
    #       - perimeter milling action will remove more material
    #   - Each line is the same length
    #   - Simplest maths, easiest to explain & visually verify

    chord_phase_offset = False

    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        return abs(2 * acos((self.arc_radius - self.max_error) / self.arc_radius))

    def get_inner_radius(self):
        """Radius each line is tangential to"""
        return abs(cos(self.wedge_angle / 2.) * self.arc_radius)

    def get_outer_radius(self):
        """Radius from which each line forms a chord"""
        return self.arc_radius


class ArcLinearizeOutside(ArcLinearizeMethod):
    """Mid-points of each line are on the original arc, first and last lines are 1/2 length"""
    # Attributes / Trade-offs:
    #   - Errors cause arc to be slightly larger
    #       - pocket milling action will remove more material
    #       - perimeter milling action will remove less material
    #   - 1st and last lines are 1/2 length of the others

    chord_phase_offset = True

    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        return abs(2 * acos(self.arc_radius / (self.arc_radius + self.max_error)))

    def get_inner_radius(self):
        """Radius each line is tangential to"""
        return self.arc_radius

    def get_outer_radius(self):
        """Radius from which each line forms a chord"""
        return abs(self.arc_radius / cos(self.wedge_angle / 2.))


class ArcLinearizeMid(ArcLinearizeMethod):
    """Lines cross original arc from tangent of arc radius - precision/2, until it reaches arc radius + precision/2"""
    # Attributes / Trade-offs:
    #   - Closest to original arc (error distances are equal inside and outside the arc)
    #   - Most complex to calculate (but who cares, that's only done once)
    #   - default linearizing method as it's probably the best

    chord_phase_offset = True

    def get_max_wedge_angle(self):
        """Calculate angular coverage of a single line reaching maximum allowable error"""
        d_radius = self.max_error / 2.
        return abs(2. * acos((self.arc_radius - d_radius) / (self.arc_radius + d_radius)))

    def get_inner_radius(self):
        """Radius each line is tangential to"""
        d_radius = self.arc_radius * (tan(self.wedge_angle / 4.) ** 2)
        return self.arc_radius - d_radius

    def get_outer_radius(self):
        """Radius from which each line forms a chord"""
        d_radius = self.arc_radius * (tan(self.wedge_angle / 4.) ** 2)
        return self.arc_radius + d_radius


DEFAULT_LA_METHOD = ArcLinearizeMid
DEFAULT_LA_PLANE = GCodeSelectXYPlane
DEFAULT_LA_DISTMODE = GCodeAbsoluteDistanceMode
DEFAULT_LA_ARCDISTMODE = GCodeIncrementalArcDistanceMode

def linearize_arc(arc_gcode, start_pos, plane=None, method_class=None,
                  dist_mode=None, arc_dist_mode=None,
                  max_error=0.01, decimal_places=3):
    """
    Convert a G2,G3 arc into a series of approsimation G1 codes
    :param arc_gcode: arc gcode to approximate (GCodeArcMove)
    :param start_pos: current machine position (Position)
    :param plane: machine's active plane (GCodePlaneSelect)
    :param method_class: method of linear approximation (ArcLinearizeMethod)
    :param dist_mode: machine's distance mode (GCodeAbsoluteDistanceMode or GCodeIncrementalDistanceMode)
    :param arc_dist_mode: machine's arc distance mode (GCodeAbsoluteArcDistanceMode or GCodeIncrementalArcDistanceMode)
    :param max_error: maximum distance approximation arcs can stray from original arc (float)
    :param decimal_places: number of decimal places gocde will be rounded to, used to mitigate risks of accumulated eror when in incremental distance mode (int)
    """
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
    if isinstance(dist_mode, GCodeAbsoluteDistanceMode):
        # given coordinates override those already defined
        arc_end_coords = dict(zip('xyz', arc_start.xyz))
        arc_end_coords.update(arc_gcode.get_param_dict('XYZ', lc=True))
        arc_end = Vector3(**arc_end_coords)
    else:
        # given coordinates are += to arc's start coords
        arc_end = arc_start + Vector3(**arc_gcode.get_param_dict('XYZ', lc=True))

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


# ==================== Un-Canning ====================

DEFAULT_SCC_PLANE = GCodeSelectXYPlane
DEFAULT_SCC_DISTMODE = GCodeAbsoluteDistanceMode
DEFAULT_SCC_RETRACTMODE = GCodeCannedCycleReturnLevel

def simplify_canned_cycle(canned_gcode, start_pos,
                          plane=None, dist_mode=None, retract_mode=None,
                          axes='XYZ'):
    """
    Simplify canned cycle into it's basic linear components
    :param canned_gcode: canned gcode to be simplified (GCodeCannedCycle)
    :param start_pos: current machine position (Position)
    :param plane: machine's active plane (GCodePlaneSelect)
    :param dist_mode: machine's distance mode (GCodeAbsoluteDistanceMode or GCodeIncrementalDistanceMode)
    :param axes: axes machine accepts (set)
    """

    # set defaults
    if plane is None:
        plane = DEFAULT_SCC_PLANE()
    if dist_mode is None:
        dist_mode = DEFAULT_SCC_DISTMODE()
    if retract_mode is None:
        retract_mode = DEFAULT_SCC_RETRACTMODE()

    # Parameter Type Assertions
    assert isinstance(canned_gcode, GCodeCannedCycle), "bad canned_gcode type: %r" % canned_gcode
    assert isinstance(start_pos, Position), "bad start_pos type: %r" % start_pos
    assert isinstance(plane, GCodePlaneSelect), "bad plane type: %r" % plane
    assert isinstance(dist_mode, (GCodeAbsoluteDistanceMode, GCodeIncrementalDistanceMode)), "bad dist_mode type: %r" % dist_mode
    assert isinstance(retract_mode, GCodeCannedReturnMode), "bad retract_mode type: %r" % retract_mode

    # TODO: implement for planes other than XY
    if not isinstance(plane, GCodeSelectXYPlane):
        raise NotImplementedError("simplifying canned cycles for planes other than X/Y has not been implemented")

    @_gcodes_abs2rel(start_pos=start_pos, dist_mode=dist_mode, axes=axes)
    def inner():
        cycle_count = 1 if (canned_gcode.L is None) else canned_gcode.L
        cur_hole_p_axis = start_pos.vector
        for i in range(cycle_count):
            # Calculate Depths
            if isinstance(dist_mode, GCodeAbsoluteDistanceMode):
                retract_depth = canned_gcode.R
                drill_depth = canned_gcode.Z
                cur_hole_p_axis = Vector3(x=canned_gcode.X, y=canned_gcode.Y)
            else:  # incremental
                retract_depth = start_pos.Z + canned_gcode.R
                drill_depth = retract_depth + canned_gcode.Z
                cur_hole_p_axis += Vector3(x=canned_gcode.X, y=canned_gcode.Y)

            if retract_depth < drill_depth:
                raise NotImplementedError("drilling upward is not supported")

            if isinstance(retract_mode, GCodeCannedCycleReturnToR):
                final_depth = retract_depth
            else:
                final_depth = start_pos.Z

            # Move above hole (height of retract_depth)
            if retract_depth > start_pos.Z:
                yield GCodeRapidMove(Z=retract_depth)
            yield GCodeRapidMove(X=cur_hole_p_axis.x, Y=cur_hole_p_axis.y)
            if retract_depth < start_pos.Z:
                yield GCodeRapidMove(Z=retract_depth)

            # Drill hole
            delta = drill_depth - retract_depth  # full depth
            if isinstance(canned_gcode, (GCodeDrillingCyclePeck, GCodeDrillingCycleChipBreaking)):
                delta = -abs(canned_gcode.Q)

            cur_depth = retract_depth
            last_depth = cur_depth
            while True:
                # Determine new depth
                cur_depth += delta
                if cur_depth < drill_depth:
                    cur_depth = drill_depth

                # Rapid to just above, then slowly drill through delta
                just_above_base = last_depth + 0.1
                if just_above_base < retract_depth:
                    yield GCodeRapidMove(Z=just_above_base)
                yield GCodeLinearMove(Z=cur_depth)
                if cur_depth <= drill_depth:
                    break  # loop stops at the bottom of the hole
                else:
                    # back up
                    if isinstance(canned_gcode, GCodeDrillingCycleChipBreaking):
                        # retract "a bit"
                        yield GCodeRapidMove(Z=cur_depth + 0.5)  # TODO: configurable retraction
                    else:
                        # default behaviour: GCodeDrillingCyclePeck
                        yield GCodeRapidMove(Z=retract_depth)

                last_depth = cur_depth

            # Dwell
            if isinstance(canned_gcode, GCodeDrillingCycleDwell):
                yield GCodeDwell(P=0.5) # TODO: configurable pause

            # Return
            yield GCodeRapidMove(Z=final_depth)

    return inner()
