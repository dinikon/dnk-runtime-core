from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.object.entity import ObjectEntity


@dataclass(frozen=True, slots=True)
class SchemaRegistryMetadataSnapshot:
    datasource: DataSourceEntity
    objects: tuple[ObjectEntity, ...]
