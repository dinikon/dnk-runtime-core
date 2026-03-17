from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata


class RuntimeSchemaFieldOrchestratorProtocol(Protocol):
    async def on_field_created(
        self,
        *,
        object_metadata: ObjectMetadata,
        field_metadata: FieldMetadata,
    ) -> None: ...

    async def on_field_deleted(
        self,
        *,
        object_metadata: ObjectMetadata,
        field_metadata: FieldMetadata,
        hard_delete: bool,
    ) -> None: ...


__all__ = ["RuntimeSchemaFieldOrchestratorProtocol"]
