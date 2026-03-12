from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.modules.custom_object.domain.value_objects import CustomObjectNameVO


@dataclass(frozen=True, slots=True)
class CustomObjectRecordEntity:
    object_name: CustomObjectNameVO
    record_id: UUID
    values: dict[str, object] = field(default_factory=dict)


__all__ = ["CustomObjectRecordEntity"]
