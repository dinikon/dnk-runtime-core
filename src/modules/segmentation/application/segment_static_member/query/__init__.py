"""Segment static member query package."""

__all__: list[str] = []
from src.modules.segmentation.application.segment_static_member.query.contact_lookup import (
    ContactLookupProtocol,
)
from src.modules.segmentation.application.segment_static_member.query.list_static_members_query import (
    ListStaticMembersQuery,
)
from src.modules.segmentation.application.segment_static_member.query.repository import (
    SegmentStaticMemberQueryRepositoryProtocol,
)
from src.modules.segmentation.application.segment_static_member.query.static_contact_audience_query import (
    StaticContactAudienceQueryProtocol,
)

__all__ = [
    "ContactLookupProtocol",
    "ListStaticMembersQuery",
    "SegmentStaticMemberQueryRepositoryProtocol",
    "StaticContactAudienceQueryProtocol",
]
