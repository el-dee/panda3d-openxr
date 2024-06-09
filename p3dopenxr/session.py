from __future__ import annotations

import ctypes
from direct.showbase.ShowBase import ShowBase
import logging
from OpenGL import GL
import platform
from typing import TYPE_CHECKING
import xr

if TYPE_CHECKING:
    from .layer import ProjectionLayer
    from .system import System


# TODO: separate package for opengl stuff
if platform.system() == "Windows":
    from OpenGL import WGL
elif platform.system() == "Linux":
    from OpenGL import GLX


def handle_key(handle):
    return hex(ctypes.cast(handle, ctypes.c_void_p).value)


stringForFormat = {
    GL.GL_COMPRESSED_R11_EAC: "COMPRESSED_R11_EAC",
    GL.GL_COMPRESSED_RED_RGTC1: "COMPRESSED_RED_RGTC1",
    GL.GL_COMPRESSED_RG_RGTC2: "COMPRESSED_RG_RGTC2",
    GL.GL_COMPRESSED_RG11_EAC: "COMPRESSED_RG11_EAC",
    GL.GL_COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT: "COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT",
    GL.GL_COMPRESSED_RGB8_ETC2: "COMPRESSED_RGB8_ETC2",
    GL.GL_COMPRESSED_RGB8_PUNCHTHROUGH_ALPHA1_ETC2: "COMPRESSED_RGB8_PUNCHTHROUGH_ALPHA1_ETC2",
    GL.GL_COMPRESSED_RGBA8_ETC2_EAC: "COMPRESSED_RGBA8_ETC2_EAC",
    GL.GL_COMPRESSED_SIGNED_R11_EAC: "COMPRESSED_SIGNED_R11_EAC",
    GL.GL_COMPRESSED_SIGNED_RG11_EAC: "COMPRESSED_SIGNED_RG11_EAC",
    GL.GL_COMPRESSED_SRGB_ALPHA_BPTC_UNORM: "COMPRESSED_SRGB_ALPHA_BPTC_UNORM",
    GL.GL_COMPRESSED_SRGB8_ALPHA8_ETC2_EAC: "COMPRESSED_SRGB8_ALPHA8_ETC2_EAC",
    GL.GL_COMPRESSED_SRGB8_ETC2: "COMPRESSED_SRGB8_ETC2",
    GL.GL_COMPRESSED_SRGB8_PUNCHTHROUGH_ALPHA1_ETC2: "COMPRESSED_SRGB8_PUNCHTHROUGH_ALPHA1_ETC2",
    GL.GL_DEPTH_COMPONENT16: "DEPTH_COMPONENT16",
    GL.GL_DEPTH_COMPONENT24: "DEPTH_COMPONENT24",
    GL.GL_DEPTH_COMPONENT32: "DEPTH_COMPONENT32",
    GL.GL_DEPTH_COMPONENT32F: "DEPTH_COMPONENT32F",
    GL.GL_DEPTH24_STENCIL8: "DEPTH24_STENCIL8",
    GL.GL_R11F_G11F_B10F: "R11F_G11F_B10F",
    GL.GL_R16_SNORM: "R16_SNORM",
    GL.GL_R16: "R16",
    GL.GL_R16F: "R16F",
    GL.GL_R16I: "R16I",
    GL.GL_R16UI: "R16UI",
    GL.GL_R32F: "R32F",
    GL.GL_R32I: "R32I",
    GL.GL_R32UI: "R32UI",
    GL.GL_R8_SNORM: "R8_SNORM",
    GL.GL_R8: "R8",
    GL.GL_R8I: "R8I",
    GL.GL_R8UI: "R8UI",
    GL.GL_RG16_SNORM: "RG16_SNORM",
    GL.GL_RG16: "RG16",
    GL.GL_RG16F: "RG16F",
    GL.GL_RG16I: "RG16I",
    GL.GL_RG16UI: "RG16UI",
    GL.GL_RG32F: "RG32F",
    GL.GL_RG32I: "RG32I",
    GL.GL_RG32UI: "RG32UI",
    GL.GL_RG8_SNORM: "RG8_SNORM",
    GL.GL_RG8: "RG8",
    GL.GL_RG8I: "RG8I",
    GL.GL_RG8UI: "RG8UI",
    GL.GL_RGB10_A2: "RGB10_A2",
    GL.GL_RGB8: "RGB8",
    GL.GL_RGB9_E5: "RGB9_E5",
    GL.GL_RGBA16_SNORM: "RGBA16_SNORM",
    GL.GL_RGBA16: "RGBA16",
    GL.GL_RGBA16F: "RGBA16F",
    GL.GL_RGBA16I: "RGBA16I",
    GL.GL_RGBA16UI: "RGBA16UI",
    GL.GL_RGBA2: "RGBA2",
    GL.GL_RGBA32F: "RGBA32F",
    GL.GL_RGBA32I: "RGBA32I",
    GL.GL_RGBA32UI: "RGBA32UI",
    GL.GL_RGBA8_SNORM: "RGBA8_SNORM",
    GL.GL_RGBA8: "RGBA8",
    GL.GL_RGBA8I: "RGBA8I",
    GL.GL_RGBA8UI: "RGBA8UI",
    GL.GL_SRGB8_ALPHA8: "SRGB8_ALPHA8",
    GL.GL_SRGB8: "SRGB8",
    GL.GL_RGB16F: "RGB16F",
    GL.GL_DEPTH32F_STENCIL8: "DEPTH32F_STENCIL8",
    GL.GL_BGR: "BGR (Out of spec)",
    GL.GL_BGRA: "BGRA (Out of spec)",
}


class Session:

    def __init__(self, system: System, base: ShowBase):
        self.logger = logging.getLogger("session")
        self.handle = None
        self.system = system
        self.base = base
        self.state = xr.SessionState.IDLE
        self.frame_state = xr.FrameState()
        self.graphics_binding = None
        if platform.system() == "Windows":
            self.graphics_binding = xr.GraphicsBindingOpenGLWin32KHR()
            self.graphics_binding.h_dc = WGL.wglGetCurrentDC()
            self.graphics_binding.h_glrc = WGL.wglGetCurrentContext()
        elif platform.system() == "Linux":
            drawable = GLX.glXGetCurrentDrawable()
            context = GLX.glXGetCurrentContext()
            display = GLX.glXGetCurrentDisplay()
            self.graphics_binding = xr.GraphicsBindingOpenGLXlibKHR(
                x_display=display,
                glx_drawable=drawable,
                glx_context=context,
            )
        else:
            raise NotImplementedError(f"Unsupported platform {platform.system()}")
        graphics_binding_pointer = ctypes.cast(
            ctypes.pointer(self.graphics_binding),
            ctypes.c_void_p)
        session_create_info = xr.SessionCreateInfo(
            next=graphics_binding_pointer,
            create_flags=xr.SessionCreateFlags(),
            system_id=system.handle,
        )
        self.handle = xr.create_session(
            system.instance.handle,
            session_create_info
        )
        self.log_swapchain_formats()
        self.log_reference_spaces()

    def destroy(self):
        if self.handle is not None:
            try:
                xr.destroy_session(self.handle)
            finally:
                self.handle = None
                self.system = None

    def get_supported_swapchain_formats(self):
        return xr.enumerate_swapchain_formats(self.handle)

    def session_active(self):
        return self.state in (
            xr.SessionState.READY,
            xr.SessionState.SYNCHRONIZED,
            xr.SessionState.VISIBLE,
            xr.SessionState.FOCUSED,
        )

    def should_render(self):
        return self.frame_state.should_render

    def on_state_changed(self, session_state_changed_event):
        event = ctypes.cast(
            ctypes.byref(session_state_changed_event), ctypes.POINTER(xr.EventDataSessionStateChanged)).contents
        if event.session is not None and handle_key(event.session) != handle_key(self.handle):
            self.logger.error(f"XrEventDataSessionStateChanged for unknown session {event.session} {self.handle}")
            return
        old_state = self.state
        self.state = xr.SessionState(event.state)
        key = ctypes.cast(self.handle, ctypes.c_void_p).value
        self.logger.info(
            f"XrEventDataSessionStateChanged: "
            f"state {str(old_state)}->{str(self.state)} "
            f"session={hex(key)} time={event.time}")
        if self.state == xr.SessionState.READY:
            if self.handle is not None:
                sbi = xr.SessionBeginInfo(self.system.view_configuration_type)
                xr.begin_session(self.handle, sbi)
        elif self.state == xr.SessionState.STOPPING:
            xr.end_session(self.session)
        elif self.state == xr.SessionState.EXITING:
            self.base.userExit()
        elif self.state == xr.SessionState.LOSS_PENDING:
            self.base.userExit()

    def poll_xr_events(self):
        while True:
            try:
                event_buffer = xr.poll_event(self.system.instance.handle)
                event_type = xr.StructureType(event_buffer.type)
                if event_type == xr.StructureType.EVENT_DATA_EVENTS_LOST:
                    events_lost = ctypes.cast(event_buffer, ctypes.POINTER(xr.EventDataEventsLost))
                    self.logger.warning(f"{events_lost} events lost")
                elif event_type == xr.StructureType.EVENT_DATA_INSTANCE_LOSS_PENDING:
                    self.logger.warning(f"XrEventDataInstanceLossPending by {event_buffer.loss_time}")
                    self.base.userExit()
                elif event_type == xr.StructureType.EVENT_DATA_SESSION_STATE_CHANGED:
                    self.on_state_changed(event_buffer)
                elif event_type == xr.StructureType.EVENT_DATA_INTERACTION_PROFILE_CHANGED:
                    pass
                elif event_type == xr.StructureType.EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING:
                    self.logger.debug(f"Ignoring event type {str(event_type)}")
                else:
                    self.logger.debug(f"Ignoring event type {str(event_type)}")
            except xr.EventUnavailable:
                break

    def wait_frame(self):
        if not self.session_active():
            return
        frame_wait_info = xr.FrameWaitInfo(None)
        self.frame_state = xr.wait_frame(self.handle, frame_wait_info)

    def begin_frame(self):
        if not self.session_active():
            return
        frame_begin_info = xr.FrameBeginInfo()
        xr.begin_frame(self.handle, frame_begin_info)

    def end_frame(self, layer: ProjectionLayer):
        if not self.session_active():
            return
        layers = []
        if self.should_render() and layer.layer_valid():
            layers.append(ctypes.byref(layer.handle))
        blend_mode = xr.EnvironmentBlendMode.OPAQUE
        frame_end_info = xr.FrameEndInfo(
            self.frame_state.predicted_display_time,
            blend_mode,
            layers=layers
        )
        xr.end_frame(self.handle, frame_end_info)

    def log_reference_spaces(self):
        spaces = xr.enumerate_reference_spaces(self.handle)
        self.logger.info(f"Available reference spaces: {len(spaces)}")
        for space in spaces:
            self.logger.debug(f"  Name: {str(xr.ReferenceSpaceType(space))}")

    def log_swapchain_formats(self) -> None:
        self.logger.debug("Swapchain Formats:")
        for sc_format in self.get_supported_swapchain_formats():
            self.logger.debug(stringForFormat[sc_format])
