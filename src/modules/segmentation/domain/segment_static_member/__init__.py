from src.modules.segmentation.domain.segment_static_member.entity import (
    SegmentStaticMember,
)
from src.modules.segmentation.domain.segment_static_member.error import (
    SegmentStaticMemberArchivedSegmentError,
    SegmentStaticMemberContactNotFoundError,
    SegmentStaticMemberError,
    SegmentStaticMemberNonStaticSegmentError,
)
from src.modules.segmentation.domain.segment_static_member.repository import (
    SegmentStaticMemberCommandRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_static_member.value_object import (
    SegmentStaticMemberIdVO,
    SegmentStaticMemberSourceTypeVO,
)

__all__ = [
    "SegmentStaticMember",
    "SegmentStaticMemberArchivedSegmentError",
    "SegmentStaticMemberCommandRepositoryProtocol",
    "SegmentStaticMemberContactNotFoundError",
    "SegmentStaticMemberError",
    "SegmentStaticMemberIdVO",
    "SegmentStaticMemberNonStaticSegmentError",
    "SegmentStaticMemberSourceTypeVO",
]
