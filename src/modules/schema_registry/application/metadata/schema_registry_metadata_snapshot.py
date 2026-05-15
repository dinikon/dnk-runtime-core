from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.relation.entity import RelationEntity


@dataclass(frozen=True, slots=True)
class SchemaRegistryMetadataSnapshot:
    """Снимок metadata schema_registry: datasource tenant и его runtime-объекты."""

    datasource: DataSourceEntity
    objects: tuple[ObjectEntity, ...]
    relations: tuple[RelationEntity, ...] = ()
