import ctypes
import platform
from typing import Sequence

import logging
import xr


ALL_SEVERITIES = (
    xr.DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT
)


ALL_TYPES = (
    xr.DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT
    | xr.DEBUG_UTILS_MESSAGE_TYPE_CONFORMANCE_BIT_EXT
)


def py_log_level(severity_flags: int):
    if severity_flags & 0x0001:  # VERBOSE
        return logging.DEBUG
    if severity_flags & 0x0010:  # INFO
        return logging.INFO
    if severity_flags & 0x0100:  # WARNING
        return logging.WARNING
    if severity_flags & 0x1000:  # ERROR
        return logging.ERROR
    return logging.CRITICAL


class Instance:
    def __init__(
            self,
            requested_extensions: Sequence[str] = None,
            application_name: str = None,
            application_version: xr.Version = None,
            api_version: xr.Version = None,
            enable_debug: bool = True,
    ) -> None:
        self.logger = logging.getLogger("instance")

        self.log_extensions()
        self.log_layers()

        self.debug_callback = xr.PFN_xrDebugUtilsMessengerCallbackEXT(self.debug_callback_py)

        if requested_extensions is None:
            requested_extensions = []
            discovered_extensions = xr.enumerate_instance_extension_properties()
            if xr.KHR_OPENGL_ENABLE_EXTENSION_NAME in discovered_extensions:
                requested_extensions.append(xr.KHR_OPENGL_ENABLE_EXTENSION_NAME)
                if xr.EXT_DEBUG_UTILS_EXTENSION_NAME in discovered_extensions:
                    requested_extensions.append(xr.EXT_DEBUG_UTILS_EXTENSION_NAME)

        if application_name is None:
            application_name = "Unknown application"
        self.application_name = application_name
        if application_version is None:
            application_version = xr.Version(0, 0, 0)
        self.logger.info(f"ApplicationName={application_name}, ApplicationVersion={application_version}")
        engine_name = "pyopenxr"
        engine_version = xr.PYOPENXR_CURRENT_API_VERSION
        self.logger.info(f"Engine version {engine_version}")
        if api_version is None:
            api_version = xr.Version(xr.XR_VERSION_MAJOR, 0, 0)
        self.logger.info(f"Request API version {api_version}")
        application_info = xr.ApplicationInfo(
            application_name=application_name,
            application_version=application_version,
            engine_name=engine_name,
            engine_version=engine_version,
            api_version=api_version,
        )

        instance_create_info = xr.InstanceCreateInfo(
            create_flags=xr.InstanceCreateFlags(),
            application_info=application_info,
            enabled_api_layer_names=[],
            enabled_extension_names=requested_extensions,
        )

        if enable_debug:
            self.logger.setLevel(logging.DEBUG)
            if xr.EXT_DEBUG_UTILS_EXTENSION_NAME in requested_extensions:
                dumci = xr.DebugUtilsMessengerCreateInfoEXT()
                dumci.message_severities = ALL_SEVERITIES
                dumci.message_types = ALL_TYPES
                dumci.user_data = None
                dumci.user_callback = self.debug_callback
                instance_create_info.next = ctypes.cast(ctypes.pointer(dumci), ctypes.c_void_p)

        self.handle = xr.create_instance(instance_create_info)
        self.log_instance_info()

    def debug_callback_py(
            self,
            severity: xr.DebugUtilsMessageSeverityFlagsEXT,
            _type: xr.DebugUtilsMessageTypeFlagsEXT,
            data: ctypes.POINTER(xr.DebugUtilsMessengerCallbackDataEXT),
            _user_data: ctypes.c_void_p,
    ) -> bool:
        d = data.contents
        # TODO structure properties to return unicode strings
        self.logger.log(py_log_level(severity), f"OpenXR: {d.function_name.decode()}: {d.message.decode()}")
        return True

    def destroy(self):
        if platform.system() != "Linux":
            if self.handle is not None:
                try:
                    xr.destroy_instance(self.handle)
                finally:
                    self.handle = None
        else:
            self.handle = None

    def _log_extensions(self, layer_name, indent: int = 0):
        """Write out extension properties for a given api_layer."""
        extension_properties = xr.enumerate_instance_extension_properties(layer_name)
        indent_str = " " * indent
        self.logger.debug(f"{indent_str}Available Extensions ({len(extension_properties)})")
        for extension in extension_properties:
            self.logger.debug(
                f"{indent_str}  Name={extension.extension_name.decode()} SpecVersion={extension.extension_version}")

    def log_extensions(self):
        self._log_extensions(layer_name=None)

    def log_instance_info(self):
        instance_properties = xr.get_instance_properties(instance=self.handle)
        self.logger.info(
            f"SpecVersion={xr.XR_CURRENT_API_VERSION} "
            f"Instance RuntimeName={instance_properties.runtime_name.decode()} "
            f"RuntimeVersion={xr.Version(instance_properties.runtime_version)}")

    def log_layers(self):
        layers = xr.enumerate_api_layer_properties()
        self.logger.info(f"Available Layers: ({len(layers)})")
        for layer in layers:
            self.logger.debug(
                f"  Name={layer.layer_name.decode()} "
                f"LayerVersion={layer.layer_version} "
                f"Description={layer.description.decode()}")
            self._log_extensions(layer_name=layer.layer_name.decode(), indent=4)
