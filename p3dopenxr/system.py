from __future__ import annotations

import ctypes
import logging
from typing import TYPE_CHECKING
import xr

from .config_view import ConfigurationView

if TYPE_CHECKING:
    from .instance import Instance


class System:
    def __init__(
            self,
            instance: Instance,
            form_factor: xr.FormFactor = xr.FormFactor.HEAD_MOUNTED_DISPLAY,
            view_configuration_type: xr.ViewConfigurationType = xr.ViewConfigurationType.PRIMARY_STEREO
    ) -> None:
        self.logger = logging.getLogger("system")
        self.handle = None
        self.instance = instance
        self.view_configuration_type = view_configuration_type
        self.views: list[ConfigurationView] = []
        self.graphics_requirements = None

        system_get_info = xr.SystemGetInfo(
            form_factor=form_factor,
        )
        self.handle = xr.get_system(instance.handle, system_get_info)
        self.logger.debug(f"Using system {hex(self.handle.value)} for form factor {str(form_factor)}")

        self.log_system_properties()
        self.log_view_configurations()

        view_configs = xr.enumerate_view_configurations(self.instance.handle, self.handle)
        if view_configuration_type.value not in view_configs:
            raise ValueError(f"View configuration type '{view_configuration_type}' not supported")

        for i, config in enumerate(xr.enumerate_view_configuration_views(
                self.instance.handle, self.handle, self.view_configuration_type)):
            view = ConfigurationView(i, config)
            self.views.append(view)

        self.create_opengl_system()

    def destroy(self):
        self.handle = None
        self.graphics_requirements = None
        self.instance = None

    def create_opengl_system(self):
        self.pxrGetOpenGLGraphicsRequirementsKHR = ctypes.cast(
            xr.get_instance_proc_addr(
                self.instance.handle,
                "xrGetOpenGLGraphicsRequirementsKHR",
            ),
            xr.PFN_xrGetOpenGLGraphicsRequirementsKHR
        )
        self.graphics_requirements = xr.GraphicsRequirementsOpenGLKHR()
        result = self.pxrGetOpenGLGraphicsRequirementsKHR(
            self.instance.handle,
            self.handle,
            ctypes.byref(self.graphics_requirements))
        result = xr.check_result(xr.Result(result))
        if result.is_exception():
            raise result

    def log_system_properties(self):
        system_properties = xr.get_system_properties(self.instance.handle, self.handle)
        self.logger.info(
            "System Properties: "
            f"Name={system_properties.system_name.decode()} "
            f"VendorId={system_properties.vendor_id}")
        self.logger.info(
            "System Graphics Properties: "
            f"MaxWidth={system_properties.graphics_properties.max_swapchain_image_width} "
            f"MaxHeight={system_properties.graphics_properties.max_swapchain_image_height} "
            f"MaxLayers={system_properties.graphics_properties.max_layer_count}")
        self.logger.info(
            "System Tracking Properties: "
            f"OrientationTracking={bool(system_properties.tracking_properties.orientation_tracking)} "
            f"PositionTracking={bool(system_properties.tracking_properties.position_tracking)}")

    def log_environment_blend_mode(self, view_config_type):
        blend_modes = xr.enumerate_environment_blend_modes(self.instance.handle, self.handle, view_config_type)
        self.logger.info("Available Environment Blend Mode:")
        for mode_value in blend_modes:
            mode = xr.EnvironmentBlendMode(mode_value)
            self.logger.info(f"    {str(mode)}")

    def log_view_configurations(self):
        view_config_types = xr.enumerate_view_configurations(self.instance.handle, self.handle)
        self.logger.info(f"Available View Configuration Types: ({len(view_config_types)})")
        for view_config_type_value in view_config_types:
            view_config_type = xr.ViewConfigurationType(view_config_type_value)
            self.logger.debug(f"  View Configuration Type: {str(view_config_type)}")
            view_config_properties = xr.get_view_configuration_properties(
                instance=self.instance.handle,
                system_id=self.handle,
                view_configuration_type=view_config_type,
            )
            self.logger.debug(f"  View configuration FovMutable={bool(view_config_properties.fov_mutable)}")
            configuration_views = xr.enumerate_view_configuration_views(
                self.instance.handle, self.handle, view_config_type)
            if configuration_views is None or len(configuration_views) < 1:
                self.logger.error("Empty view configuration type")
            else:
                for i, view in enumerate(configuration_views):
                    self.logger.debug(
                        f"    View [{i}]: Recommended Width={view.recommended_image_rect_width} "
                        f"Height={view.recommended_image_rect_height} "
                        f"SampleCount={view.recommended_swapchain_sample_count}")
                    self.logger.debug(
                        f"    View [{i}]:     Maximum Width={view.max_image_rect_width} "
                        f"Height={view.max_image_rect_height} "
                        f"SampleCount={view.max_swapchain_sample_count}")
            self.log_environment_blend_mode(view_config_type)
