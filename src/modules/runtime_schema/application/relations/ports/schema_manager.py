from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
)


class RelationSchemaManagerProtocol(Protocol):
    async def ensure_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        source_field: FieldMetadata | None,
        target_object: ObjectMetadata,
        target_field: FieldMetadata | None,
    ) -> None: ...

    async def drop_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        source_field: FieldMetadata | None,
        target_object: ObjectMetadata,
        target_field: FieldMetadata | None,
    ) -> None: ...
