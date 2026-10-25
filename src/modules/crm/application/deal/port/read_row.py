from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DealReadRowDTO:
    """Проекция собственных полей Deal, без SQL и поведения Domain."""

    id: UUID
    title: str
    funnel_id: UUID
    stage_id: UUID
    position_revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    contact_ids: tuple[UUID, ...]
    company_ids: tuple[UUID, ...]
    source_lead_id: UUID | None
    source_lead_snapshot: dict[str, str | None] | None
    lifecycle_state: str
