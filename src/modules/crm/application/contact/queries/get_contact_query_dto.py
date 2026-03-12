from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContactQueryDTO:
    tenant_id: UUID
    contact_id: UUID


__all__ = ["GetContactQueryDTO"]
