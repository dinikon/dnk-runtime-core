from src.modules.segmentation.presentation.http.segment_snapshot_member.controllers import (
    list_segment_snapshot_members,
)

routers = (list_segment_snapshot_members.router,)

__all__ = ["routers"]
