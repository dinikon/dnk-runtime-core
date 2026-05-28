from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.dto.contact_summary_dto import (
    ContactSummaryDTO,
)


@dataclass(frozen=True, slots=True)
class StaticMemberDTO:
    """Read model for a static Contact segment member."""

    id: UUID
    segment_id: UUID
    contact_id: UUID
    source_type: str
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    contact: ContactSummaryDTO | None = None


__all__ = ["StaticMemberDTO"]
