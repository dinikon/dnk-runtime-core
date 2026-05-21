from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ObjectFeatureConfigDTO:
    """DTO feature config runtime-объекта."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    object_id: UUID
    feature_code: str
    kind: str
    status: str
    config: dict[str, Any]
    is_locked: bool
    locked_reason: str | None


__all__ = ["ObjectFeatureConfigDTO"]
