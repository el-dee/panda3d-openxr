import ctypes
import logging
from panda3d.core import CS_yup_right, CS_default, LMatrix4, LPoint3, LQuaternion
import xr

from .session import Session
from .space import Space


class ActionSet:

    def __init__(self, session: Session, app_space: Space, name: str, localized_name: str, priority: int = 0):
        self.logger = logging.getLogger("actionset::" + name)
        self.session = session
        self.app_space = app_space
        self.coord_mat = LMatrix4.convert_mat(CS_yup_right, CS_default)
        self.pose_links = {}
        instance = self.session.system.instance
        action_set_info = xr.ActionSetCreateInfo(
            action_set_name=name,
            localized_action_set_name=localized_name,
            priority=priority,
        )
        self.handle = xr.create_action_set(instance.handle, action_set_info)

        self.hands_path_string = [
            "/user/hand/left",
            "/user/hand/right",
            ]

        self.hands_path = [xr.string_to_path(instance.handle, path) for path in self.hands_path_string]

        self.hand_pose_action = xr.create_action(
            action_set=self.handle,
            create_info=xr.ActionCreateInfo(
                action_type=xr.ActionType.POSE_INPUT,
                action_name="hand_pose",
                localized_action_name="Hand Pose",
                count_subaction_paths=len(self.hands_path),
                subaction_paths=self.hands_path,
            ),
        )
        self.hand_pose_path = [
            xr.string_to_path(instance.handle, "/user/hand/left/input/grip/pose"),
            xr.string_to_path(instance.handle, "/user/hand/right/input/grip/pose")]
        # Suggest bindings for KHR Simple.
        khr_bindings = [
            # Fall back to a click input for the grab action.
            xr.ActionSuggestedBinding(self.hand_pose_action, self.hand_pose_path[0]),
            xr.ActionSuggestedBinding(self.hand_pose_action, self.hand_pose_path[1]),
        ]

        self.hands_space = []
        for hand_path in self.hands_path:
            action_space_info = xr.ActionSpaceCreateInfo(
                action=self.hand_pose_action,
                subaction_path=hand_path,
                )
            self.hands_space.append(xr.create_action_space(
                session=self.session.handle,
                create_info=action_space_info,
            ))

        xr.suggest_interaction_profile_bindings(
            instance=instance.handle,
            suggested_bindings=xr.InteractionProfileSuggestedBinding(
                interaction_profile=xr.string_to_path(
                    instance.handle,
                    "/interaction_profiles/khr/simple_controller",
                ),
                suggested_bindings=khr_bindings,
            ),
        )

    def link_pose(self, path, nodepath):
        self.pose_links[path] = nodepath

    def attach(self) -> None:
        xr.attach_session_action_sets(
            session=self.session.handle,
            attach_info=xr.SessionActionSetsAttachInfo(
                count_action_sets=1,
                action_sets=ctypes.pointer(self.handle),
            ),
        )

    def poll_actions(self):
        if not self.session.session_active():
            return
        active_action_set = xr.ActiveActionSet(self.handle, xr.NULL_PATH)
        xr.sync_actions(
            self.session.handle,
            xr.ActionsSyncInfo(
                count_active_action_sets=1,
                active_action_sets=ctypes.pointer(active_action_set)
            ),
        )
        for path_string, hand_path, hand_space in zip(self.hands_path_string, self.hands_path, self.hands_space):
            nodepath = self.pose_links[path_string]
            state = xr.get_action_state_pose(
                session=self.session.handle,
                get_info=xr.ActionStateGetInfo(
                    action=self.hand_pose_action,
                    subaction_path=hand_path,
                ),
            )
            if state.is_active:
                space_location = xr.locate_space(
                    space=hand_space,
                    base_space=self.app_space.handle,
                    time=self.session.frame_state.predicted_display_time,
                )
                flags = space_location.location_flags
                pose_valid = (
                    flags & xr.SPACE_LOCATION_POSITION_VALID_BIT != 0 and
                    flags & xr.SPACE_LOCATION_ORIENTATION_VALID_BIT != 0)
                if state.is_active and pose_valid:
                    nodepath.unstash()
                    nodepath.set_pos(self.coord_mat.xform_point(LPoint3(*space_location.pose.position)))
                    quat = space_location.pose.orientation
                    # TODO: Check why we can't use coord_mat here
                    nodepath.set_quat(LQuaternion(quat.w, quat.x, -quat.z, quat.y))
                else:
                    nodepath.stash()
            else:
                nodepath.stash()

    def destroy(self):
        if self.handle is not None:
            xr.destroy_action_set(self.handle)
            self.handle = None
