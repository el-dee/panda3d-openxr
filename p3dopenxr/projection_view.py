from __future__ import annotations

import math
from panda3d.core import LMatrix4, LPoint3, LQuaternion
from panda3d.core import CS_default, CS_yup_right
import xr


class ProjectionView:

    def __init__(self, index: int, view: xr.CompositionLayerProjectionView):
        self.index = index
        self.view = view
        self.coord_mat = LMatrix4.convert_mat(CS_yup_right, CS_default)
        self.coord_mat_inv = LMatrix4.convert_mat(CS_default, CS_yup_right)

    def set_view(self, view):
        self.view = view

    @property
    def pose(self):
        return self.view.pose

    @property
    def position(self):
        return self.coord_mat.xform_point(LPoint3(*self.view.pose.position))

    @property
    def orientation(self):
        quat = self.view.pose.orientation
        # TODO: Check why we can't use coord_mat here
        return LQuaternion(quat.w, quat.x, -quat.z, quat.y)

    @property
    def fov(self):
        return self.view.fov

    def calc_projection_matrix(self, near_z: float, far_z: float) -> LMatrix4:
        tan_left = math.tan(self.fov.angle_left)
        tan_right = math.tan(self.fov.angle_right)
        tan_down = math.tan(self.fov.angle_down)
        tan_up = math.tan(self.fov.angle_up)
        mat = self._create_projection(tan_left, tan_right, tan_up, tan_down, near_z, far_z)
        return self.coord_mat_inv * mat

    @staticmethod
    def _create_projection(
            tan_angle_left: float, tan_angle_right: float, tan_angle_up: float,
            tan_angle_down: float, near_z: float, far_z: float) -> LMatrix4:
        """
        Creates a projection matrix based on the specified dimensions.
        The projection matrix transforms -Z=forward, +Y=up, +X=right to the appropriate clip space for the graphics API
        The far plane is placed at infinity if far_z <= near_z.
        An infinite projection matrix is preferred for rasterization because, except for
        things *right* up against the near plane, it always provides better precision:
                     "Tightening the Precision of Perspective Rendering"
                     Paul Upchurch, Mathieu Desbrun
                     Journal of Graphics Tools, Volume 16, Issue 1, 2012
        """
        tan_angle_width = tan_angle_right - tan_angle_left
        # Set to tan_angle_up - tan_angle_down for a clip space with positive Y up
        tan_angle_height = tan_angle_up - tan_angle_down
        # Set to near_z for a [-1,1] Z clip space
        offset_z = near_z
        m = [0] * 16
        if far_z <= near_z:
            # place the far plane at infinity
            m[0] = 2.0 / tan_angle_width
            m[4] = 0.0
            m[8] = (tan_angle_right + tan_angle_left) / tan_angle_width
            m[12] = 0.0

            m[1] = 0.0
            m[5] = 2.0 / tan_angle_height
            m[9] = (tan_angle_up + tan_angle_down) / tan_angle_height
            m[13] = 0.0

            m[2] = 0.0
            m[6] = 0.0
            m[10] = -1.0
            m[14] = -(near_z + offset_z)

            m[3] = 0.0
            m[7] = 0.0
            m[11] = -1.0
            m[15] = 0.0
        else:
            # normal projection
            m[0] = 2.0 / tan_angle_width
            m[4] = 0.0
            m[8] = (tan_angle_right + tan_angle_left) / tan_angle_width
            m[12] = 0.0

            m[1] = 0.0
            m[5] = 2.0 / tan_angle_height
            m[9] = (tan_angle_up + tan_angle_down) / tan_angle_height
            m[13] = 0.0

            m[2] = 0.0
            m[6] = 0.0
            m[10] = -(far_z + offset_z) / (far_z - near_z)
            m[14] = -(far_z * (near_z + offset_z)) / (far_z - near_z)

            m[3] = 0.0
            m[7] = 0.0
            m[11] = -1.0
            m[15] = 0.0
        return LMatrix4(*m)
