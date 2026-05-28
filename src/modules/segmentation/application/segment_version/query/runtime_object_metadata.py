from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.modules.schema_registry.runtime import RuntimeObjectDescriptor
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class SegmentVersionRuntimeRelationMetadata:
    """Public-name relation metadata used by segment version DSL validation."""

    name: str
    source_object: str
    target_object: str
    relation_type: str
    fk_field: str | None
    referenced_object: str | None
    referenced_field: str | None
    owning_object: str | None


class RuntimeObjectMetadataProtocol(Protocol):
    """Read-only metadata port for segment version DSL validation."""

    async def resolve_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        """Resolve a runtime object descriptor by public singular object name."""
        ...

    async def field_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> bool:
        """Return whether a public object has the field."""
        ...

    async def field_type(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> str | None:
        """Return a field type code or None when field/object is unknown."""
        ...

    async def resolve_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> SegmentVersionRuntimeRelationMetadata | None:
        """Resolve relation by source object and public relation name."""
        ...

    async def relation_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> bool:
        """Return whether relation can be resolved."""
        ...


__all__ = [
    "RuntimeObjectMetadataProtocol",
    "SegmentVersionRuntimeRelationMetadata",
]
