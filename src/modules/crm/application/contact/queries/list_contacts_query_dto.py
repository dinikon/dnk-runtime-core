from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListContactsQueryDTO:
    tenant_id: UUID
    limit: int = 50
    offset: int = 0


__all__ = ["ListContactsQueryDTO"]
