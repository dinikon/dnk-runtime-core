from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteRelationCommand:
    """Command удаления custom relation."""

    tenant_id: EntityIdVO
    relation_id: RuntimeRelationIdVO


__all__ = ["DeleteRelationCommand"]
