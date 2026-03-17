from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WriteRuntimeValuesCommand:
    tenant_id: UUID
    object_name_singular: str
    record_id: UUID
    values: dict[str, object | None]


__all__ = ["WriteRuntimeValuesCommand"]
