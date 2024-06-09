from __future__ import annotations

from typing import TYPE_CHECKING
import xr

if TYPE_CHECKING:
    from .session import Session


class Space:
    def __init__(
            self,
            session: Session,
            reference_space_type: str = "Stage"
    ):
        reference_space_create_info = self.get_xr_reference_space_create_info(reference_space_type)
        self.handle = xr.create_reference_space(session.handle, reference_space_create_info)

    def get_xr_reference_space_create_info(self, reference_space_type: str) -> xr.ReferenceSpaceCreateInfo:
        create_info = xr.ReferenceSpaceCreateInfo(
            pose_in_reference_space=xr.Posef(),
        )
        if reference_space_type == "View":
            create_info.reference_space_type = xr.ReferenceSpaceType.VIEW
        elif reference_space_type == "Local":
            create_info.reference_space_type = xr.ReferenceSpaceType.LOCAL
        elif reference_space_type == "Stage":
            create_info.reference_space_type = xr.ReferenceSpaceType.STAGE
        else:
            raise ValueError(f"Unknown reference space type '{reference_space_type}'")
        return create_info

    def destroy(self):
        if self.handle is not None:
            xr.destroy_space(self.handle)
            self.handle = None
