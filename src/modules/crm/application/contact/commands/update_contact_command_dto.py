from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateContactCommandDTO:
    tenant_id: UUID
    contact_id: UUID
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    custom_fields: dict[str, object] = field(default_factory=dict)


__all__ = ["UpdateContactCommandDTO"]
