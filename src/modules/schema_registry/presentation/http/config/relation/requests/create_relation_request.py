from __future__ import annotations

from pydantic import BaseModel

from src.modules.schema_registry.presentation.http.config.relation.requests.relation_request import (
    RelationRequestSchema,
)


class CreateRelationRequestSchema(BaseModel):
    """Pydantic-схема создания custom relation."""

    relation: RelationRequestSchema


__all__ = ["CreateRelationRequestSchema"]
