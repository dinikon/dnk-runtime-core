from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListCustomObjectsQuery:
    """Query списка кастомных объектов tenant."""

    tenant_id: EntityIdVO


__all__ = ["ListCustomObjectsQuery"]
