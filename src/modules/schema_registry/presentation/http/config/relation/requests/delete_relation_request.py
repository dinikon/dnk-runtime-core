from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DeleteRelationRequestSchema(BaseModel):
    """Pydantic-схема удаления custom relation."""

    relation_id: UUID


__all__ = ["DeleteRelationRequestSchema"]
