from __future__ import annotations

import logging
import xr

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Session
    from .config_view import ConfigurationView


class Swapchain:
    def __init__(
            self,
            session: Session,
            view: ConfigurationView,
            sc_format: int,
            width: Optional[int] = None,
            height: Optional[int] = None,
            sample_count: Optional[int] = None):
        self.logger = logging.getLogger('swapchain')
        self.session = session
        self.view = view
        self.handle: xr.Swapchain = None
        self.images = None
        self.logger.info(
            "Creating swapchain for "
            f"view {view.index} with dimensions "
            f"Width={view.recommended_image_rect_width} "
            f"Height={view.recommended_image_rect_height} "
            f"SampleCount={view.recommended_swapchain_sample_count}")

        if width is None:
            width = view.recommended_image_rect_width
        self.width = width
        if height is None:
            height = view.recommended_image_rect_height
        self.height = height
        if sample_count is None:
            sample_count = view.recommended_swapchain_sample_count
        self.sample_count = sample_count

        swapchain_create_info = xr.SwapchainCreateInfo(
            array_size=1,
            format=sc_format,
            width=self.width,
            height=self.height,
            mip_count=1,
            face_count=1,
            sample_count=self.sample_count,
            usage_flags=xr.SwapchainUsageFlags.SAMPLED_BIT | xr.SwapchainUsageFlags.COLOR_ATTACHMENT_BIT,
        )

        self.handle = xr.create_swapchain(session.handle, swapchain_create_info)
        self.images = xr.enumerate_swapchain_images(self.handle, xr.SwapchainImageOpenGLKHR)
        for i, si in enumerate(self.images):
            self.logger.debug(f"Swapchain image {i} type = {xr.StructureType(si.type)}")

    def destroy(self):
        if self.handle is not None:
            try:
                xr.destroy_swapchain(self.handle)
            finally:
                self.handle = None
                self.images = None

    def acquire_image_info(self):
        ai = xr.SwapchainImageAcquireInfo(None)
        swapchain_index = xr.acquire_swapchain_image(self.handle, ai)
        wi = xr.SwapchainImageWaitInfo(xr.INFINITE_DURATION)
        xr.wait_swapchain_image(self.handle, wi)
        sw_image = self.images[swapchain_index]
        return sw_image

    def release_image_info(self):
        ri = xr.SwapchainImageReleaseInfo()
        xr.release_swapchain_image(self.handle, ri)
