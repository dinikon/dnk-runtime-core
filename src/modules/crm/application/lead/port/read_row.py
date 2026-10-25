from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LeadReadRowDTO:
    """Проекция собственных полей Lead, без SQL и поведения Domain."""

    id: UUID
    title: str
    funnel_id: UUID
    stage_id: UUID
    position_revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    company_name: str | None
    contact_id: UUID | None
    company_id: UUID | None
    conversion_result: dict[str, object] | None
