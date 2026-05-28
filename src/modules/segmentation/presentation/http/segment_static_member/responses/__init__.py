"""Segment static member HTTP response schemas."""

__all__: list[str] = []
from src.modules.segmentation.presentation.http.segment_static_member.responses.contact_summary_response import (
    ContactSummaryResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_static_member.responses.list_static_members_response import (
    ListStaticMembersResponseSchema,
)
from src.modules.segmentation.presentation.http.segment_static_member.responses.static_member_response import (
    StaticMemberResponseSchema,
)

__all__ = [
    "ContactSummaryResponseSchema",
    "ListStaticMembersResponseSchema",
    "StaticMemberResponseSchema",
]
