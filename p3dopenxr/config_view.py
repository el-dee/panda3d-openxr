from __future__ import annotations

import xr


class ConfigurationView:

    def __init__(self, index: int, config: xr.ViewConfigurationView):
        self.index = index
        self.config = config

    @property
    def max_image_rect_width(self) -> int:
        return self.config.max_image_rect_width

    @property
    def max_image_rect_height(self) -> int:
        return self.config.max_image_rect_height

    @property
    def max_swapchain_sample_count(self) -> int:
        return self.config.max_swapchain_sample_count

    @property
    def recommended_image_rect_width(self) -> int:
        return self.config.recommended_image_rect_width

    @property
    def recommended_image_rect_height(self) -> int:
        return self.config.recommended_image_rect_height

    @property
    def recommended_swapchain_sample_count(self) -> int:
        return self.config.recommended_swapchain_sample_count
