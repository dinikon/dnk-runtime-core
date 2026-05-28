from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.modules.segmentation.presentation.http.segment_static_member.responses.contact_summary_response import (
    ContactSummaryResponseSchema,
)


class StaticMemberResponseSchema(BaseModel):
    """HTTP response static segment member."""

    id: UUID
    segment_id: UUID
    contact_id: UUID
    source_type: str
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    contact: ContactSummaryResponseSchema | None


__all__ = ["StaticMemberResponseSchema"]
