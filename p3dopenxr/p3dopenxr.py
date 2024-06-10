import atexit
from direct.task.TaskManagerGlobal import taskMgr
from functools import partial
import logging
from OpenGL import GL
import os
from panda3d.core import load_prc_file_data, NodePath, LMatrix4
from panda3d.core import FrameBufferProperties, PythonCallbackObject
from panda3d.core import Camera, MatrixLens
import xr

from .actionset import ActionSet
from .instance import Instance
from .layer import ProjectionLayer
from .session import Session
from .space import Space
from .swapchain import Swapchain
from .system import System

logging.basicConfig(level=logging.DEBUG)

# Disable v-sync, it will be managed by waitGetPoses()
load_prc_file_data("", "sync-video 0")
# NVidia driver requires this env variable to be set to 0 to disable v-sync
os.environ['__GL_SYNC_TO_VBLANK'] = "0"
# MESA OpenGL drivers requires this env variable to be set to 0 to disable v-sync
os.environ['vblank_mode'] = "0"


class P3DOpenXR():
    def __init__(self, base=None):
        """
        Wrapper around pyopenxr to allow it to work with Panda3D.
        See the init() method below for the actual initialization.
        """

        self.logger = logging.getLogger("p3dopenxr")
        if base is None:
            base = __builtins__.get('base')
        self.base = base
        self.buffers = []
        self.cams = []
        self.dr: list = []
        self.nextsort = self.base.win.getSort() - 1000
        self.instance: Instance = None
        self.system: System = None
        self.session: Session = None
        self.action_set: ActionSet = None
        self.app_space: Space = None
        self.tracking_space: Space = None
        self.view_space: Space = None
        self.swapchains: list[Swapchain] = []
        self.layer: ProjectionLayer = None
        self.end_frame_called = False
        self.near: float = None
        self.far: float = None
        atexit.register(self.destroy)

    def create_default_fb_props(self):
        props = FrameBufferProperties(FrameBufferProperties.get_default())
        props.set_back_buffers(0)
        props.set_rgb_color(1)
        props.set_alpha_bits(0)
        props.set_srgb_color(True)
        props.set_depth_bits(1)
        return props

    def create_buffer(self, name, width, height, fb_props):
        """
        Create a render buffer with the given properties.
        """

        buffer = self.base.win.make_texture_buffer(name, width, height, to_ram=False, fbp=fb_props)
        if buffer is not None:
            buffer.disable_clears()
            buffer.set_active(True)
            buffer.clear_render_textures()
            buffer.set_sort(self.nextsort)
            self.nextsort += 1
        else:
            self.logger.error("Could not create buffer")
        return buffer

    def create_display_region(self, buffer, camera, callback, cc=None):
        """
        Create and configure a display region and attach it the given camera and draw callback.
        """
        dr = buffer.make_display_region(0, 1, 0, 1)
        dr.set_camera(camera)
        dr.set_active(1)
        dr.disable_clears()
        if callback is not None:
            dr.set_draw_callback(PythonCallbackObject(callback))
        if cc is not None:
            dr.set_clear_color_active(1)
            dr.set_clear_color(cc)

    def create_camera(self, name: str) -> Camera:
        """
        Create a camera with the given projection matrix.
        """

        cam_node = Camera(name)
        lens = MatrixLens()
        lens.set_user_mat(LMatrix4())
        cam_node.set_lens(lens)
        return cam_node

    def disable_main_cam(self):
        """
        Disable the default camera (but not remove it).
        """

        self.empty_world = NodePath()
        self.base.camera.reparent_to(self.empty_world)

    def init(self, near=0.01, far=100.0, root=None, fb_props=None, mirroring=0):
        if fb_props is None:
            fb_props = self.create_default_fb_props()
        sc_format = self.fb_props_to_gl_mode(fb_props)
        self.instance = Instance()
        self.system = System(self.instance)
        self.session = Session(self.system, self.base)
        self.tracking_space = Space(self.session, reference_space_type='Stage')
        self.view_space = Space(self.session, reference_space_type='View')
        self.app_space = self.tracking_space
        for view in self.system.views:
            self.swapchains.append(Swapchain(self.session, view, sc_format=sc_format, sample_count=1))
        self.layer = ProjectionLayer(self.session, self.app_space, len(self.system.views))
        self.action_set = ActionSet(self.session, self.app_space, "default", "Default action set", priority=0)

        # Create the tracking space anchors
        if root is None:
            root = self.base.render
        self.tracking_space_anchor = root.attach_new_node('tracking-space-anchor')
        self.hmd_anchor = self.tracking_space_anchor.attach_new_node('hmd-anchor')
        self.view_space_anchor = root.attach_new_node('view-space')
        self.left_hand_anchor = self.tracking_space_anchor.attach_new_node('left-hand-anchor')
        self.right_hand_anchor = self.tracking_space_anchor.attach_new_node('right-hand-anchor')

        # Create the cameras and attach them in the tracking space
        self.near = near
        self.far = far

        for i, swapchain in enumerate(self.swapchains):
            last = (i == len(self.swapchains) - 1)
            cam_node = self.create_camera(f'cam-{i}')
            cam = self.tracking_space_anchor.attach_new_node(cam_node)
            self.cams.append(cam)
            buffer = self.create_buffer(
                f"xr-render-buffer-{i}", swapchain.width, swapchain.height, fb_props)
            self.dr.append(self.create_display_region(buffer, self.cams[i], callback=partial(self.render, i, last)))
            self.buffers.append(buffer)

        self.action_set.link_pose('/user/hand/left', self.left_hand_anchor)
        self.action_set.link_pose('/user/hand/right', self.right_hand_anchor)

        self.action_set.attach()

        # The main camera is useless, so we disable it
        self.disable_main_cam()

        self.logger.info("Eye mirroring disabled")

        # Launch the main task that will synchronize Panda3D with OpenXR
        # TODO: The sort number should be configurable.
        self.task = taskMgr.add(self.poll_events_task, "openXRPollEvents", sort=-1000)
        self.task = taskMgr.add(self.wait_frame_task, "openXRWaitFrame", sort=-999)
        self.task = taskMgr.add(self.update_views_task, "openXRUpdateViews", sort=-100)
        self.task = taskMgr.add(self.poll_actions_task, "openXRPollActions", sort=-40)
        self.task = taskMgr.add(self.end_frame_task, "openXREndFrame", sort=1000)

    def destroy(self):
        if self.layer is not None:
            self.logger.debug("Destroy layer")
            self.layer.destroy()
        for swapchain in self.swapchains:
            self.logger.debug("Destroy swapchains")
            swapchain.destroy()
        if self.tracking_space is not None:
            self.logger.debug("Destroy tracking space")
            self.tracking_space.destroy()
        if self.view_space is not None:
            self.logger.debug("Destroy view space")
            self.view_space.destroy()
        if self.session is not None:
            self.logger.debug("Destroy session")
            self.session.destroy()
        if self.system is not None:
            self.logger.debug("Destroy system")
            self.system.destroy()
        if self.instance is not None:
            self.logger.debug("Destroy instance")
            self.instance.destroy()
        self.logger.debug("All object destroyed")

    def poll_events_task(self, task):
        self.session.poll_xr_events()
        return task.cont

    def wait_frame_task(self, task):
        if not self.session.session_active():
            return task.cont
        self.session.wait_frame()
        self.session.begin_frame()
        self.end_frame_called = False
        return task.cont

    def update_views_task(self, task):
        if not self.session.session_active() or not self.session.should_render():
            return task.cont
        self.layer.update_views(self.swapchains)
        if not self.layer.pose_valid:
            return task.cont
        for cam, view in zip(self.cams, self.layer.views):
            cam.node().get_lens().set_user_mat(view.calc_projection_matrix(self.near, self.far))
            cam.set_pos(view.position)
            cam.set_quat(view.orientation)
        return task.cont

    def poll_actions_task(self, task):
        try:
            self.action_set.poll_actions()
        except xr.exception.SessionNotFocused:
            pass
        return task.cont

    def render(self, index, last, cbdata):
        if not self.session.session_active() or not self.session.should_render() or not self.layer.pose_valid:
            return
        swapchain = self.swapchains[index]
        image_info = swapchain.acquire_image_info()
        self.layer.render_swapchain(index)
        GL.glFramebufferTexture(
            GL.GL_DRAW_FRAMEBUFFER,
            GL.GL_COLOR_ATTACHMENT0,
            image_info.image,
            0
        )
        GL.glClearDepth(1.0)
        GL.glClearColor(0, 0, 0, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)
        # Perform the actual Draw jobs
        cbdata.upcall()
        swapchain.release_image_info()
        if last:
            self.session.end_frame(self.layer)
            self.end_frame_called = True

    def end_frame_task(self, task):
        if not self.session.session_active():
            return task.cont
        if not self.end_frame_called:
            self.session.end_frame(self.layer)
            self.end_frame_called = True
        return task.cont

    def fb_props_to_gl_mode(self, fb_props: FrameBufferProperties):
        """
        Convert a frame buffer configuration into an OpenGL format
        """

        if fb_props.alpha_bits == 0:
            if fb_props.srgb_color:
                gl_format = GL.GL_SRGB8
            elif (fb_props.color_bits > 16 * 3 or
                  fb_props.red_bits > 16 or
                  fb_props.green_bits > 16 or
                  fb_props.blue_bits > 16):
                # 32-bit, which is always floating-point.
                if fb_props.blue_bits > 0 or fb_props.color_bits == 1 or fb_props.color_bits > 32 * 2:
                    gl_format = GL.GL_RGB32F
                elif fb_props.green_bits > 0 or fb_props.color_bits > 32:
                    gl_format = GL.GL_RG32F
                else:
                    gl_format = GL.GL_R32F
            elif fb_props.float_color:
                # 16-bit floating-point.
                if fb_props.blue_bits > 10 or fb_props.color_bits == 1 or fb_props.color_bits > 32:
                    gl_format = GL.GL_RGB16F
                elif fb_props.blue_bits > 0:
                    if fb_props.red_bits > 11 or fb_props.green_bits > 11:
                        gl_format = GL.GL_RGB16F
                    else:
                        gl_format = GL.GL_R11F_G11F_B10F
                elif fb_props.green_bits > 0 or fb_props.color_bits > 16:
                    gl_format = GL.GL_RG16F
                else:
                    gl_format = GL.GL_R16F
            elif (fb_props.color_bits > 10 * 3 or
                  fb_props.red_bits > 10 or
                  fb_props.green_bits > 10 or
                  fb_props.blue_bits > 10):
                # 16-bit normalized.
                if fb_props.blue_bits > 0 or fb_props.color_bits == 1 or fb_props.color_bits > 16 * 2:
                    gl_format = GL.GL_RGBA16
                elif fb_props.green_bits > 0 or fb_props.color_bits > 16:
                    gl_format = GL.GL_RG16
                else:
                    gl_format = GL.GL_R16
            elif (fb_props.color_bits > 8 * 3 or
                  fb_props.red_bits > 8 or
                  fb_props.green_bits > 8 or
                  fb_props.blue_bits > 8):
                gl_format = GL.GL_RGB10_A2
            else:
                gl_format = GL.GL_RGB
        else:
            if fb_props.srgb_color:
                gl_format = GL.GL_SRGB8_ALPHA8
            elif fb_props.float_color:
                if fb_props.color_bits > 16 * 3:
                    gl_format = GL.GL_RGBA32F
                else:
                    gl_format = GL.GL_RGBA16F
            else:
                if fb_props.color_bits > 16 * 3:
                    gl_format = GL.GL_RGBA32F
                elif fb_props.color_bits > 8 * 3:
                    gl_format = GL.GL_RGBA16
                else:
                    gl_format = GL.GL_RGBA
        return gl_format
