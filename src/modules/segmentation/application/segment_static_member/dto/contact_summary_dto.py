from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactSummaryDTO:
    """Minimal Contact summary for segment member read models."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    status: str | None


__all__ = ["ContactSummaryDTO"]
