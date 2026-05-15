from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.config.relation.command.relation_input import (
    RelationInput,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateRelationCommand:
    """Command создания custom relation."""

    tenant_id: EntityIdVO
    relation: RelationInput


__all__ = ["CreateRelationCommand"]
