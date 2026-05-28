from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_static_member.responses.static_member_response import (
    StaticMemberResponseSchema,
)


class ListStaticMembersResponseSchema(BaseModel):
    """HTTP response for static segment members list."""

    items: list[StaticMemberResponseSchema]
    count: int


__all__ = ["ListStaticMembersResponseSchema"]
