from src.modules.segmentation.application.segment_version.query.get_segment_version_query import (
    GetSegmentVersionQuery,
)
from src.modules.segmentation.application.segment_version.query.list_segment_versions_query import (
    ListSegmentVersionsQuery,
)
from src.modules.segmentation.application.segment_version.query.repository import (
    SegmentVersionQueryRepositoryProtocol,
)

__all__ = [
    "GetSegmentVersionQuery",
    "ListSegmentVersionsQuery",
    "SegmentVersionQueryRepositoryProtocol",
]
