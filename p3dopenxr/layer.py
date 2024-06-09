from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import xr

from .projection_view import ProjectionView

if TYPE_CHECKING:
    from .session import Session
    from .space import Space
    from .swapchain import Swapchain


class ProjectionLayer:
    def __init__(self, session: Session, space: Space, nb_views: int):
        self.logger = logging.getLogger("layer")
        self.session = session
        self.space = space
        layer_flags = 0
        self.views: list[ProjectionView] = []
        views: list[xr.CompositionLayerProjectionView] = []
        for i in range(nb_views):
            view = xr.CompositionLayerProjectionView()
            views.append(view)
            self.views.append(ProjectionView(i, view))
        self.render_status: list[bool] = [False] * nb_views
        self.pose_valid: bool = False
        self.handle = xr.CompositionLayerProjection(layer_flags, space.handle, views=views)

    def update_views(self, swapchains: list[Swapchain]) -> None:
        view_state, views = xr.locate_views(
            session=self.session.handle,
            view_locate_info=xr.ViewLocateInfo(
                view_configuration_type=self.session.system.view_configuration_type,
                display_time=self.session.frame_state.predicted_display_time,
                space=self.space.handle,
            ),
        )
        for i, (layer_view, view, swapchain) in enumerate(zip(self.handle.views, views, swapchains)):
            self.views[i].set_view(view)
            layer_view.pose = view.pose
            layer_view.fov = view.fov
            layer_view.sub_image.swapchain = swapchain.handle
            layer_view.sub_image.image_rect.offset[:] = [0, 0]
            layer_view.sub_image.image_rect.extent[:] = [swapchain.width, swapchain.height]
        self.render_status = [False] * len(swapchains)
        flags = view_state.view_state_flags
        self.pose_valid = (
            flags & xr.VIEW_STATE_POSITION_VALID_BIT != 0 and flags & xr.VIEW_STATE_ORIENTATION_VALID_BIT != 0)

    def render_swapchain(self, index: int) -> bool:
        self.render_status[index] = True

    def layer_valid(self) -> bool:
        return self.pose_valid and False not in self.render_status

    def destroy(self) -> None:
        self.handle = None
