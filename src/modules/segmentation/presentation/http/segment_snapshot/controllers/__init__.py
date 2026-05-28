from src.modules.segmentation.presentation.http.segment_snapshot.controllers import (
    create_segment_snapshot,
    get_segment_snapshot,
    list_segment_snapshots,
)

routers = (
    create_segment_snapshot.router,
    list_segment_snapshots.router,
    get_segment_snapshot.router,
)

__all__ = ["routers"]
