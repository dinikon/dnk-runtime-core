from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.service.schema_registry_metadata_service import (
    SchemaRegistryMetadataService,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep,
    ObjectServiceDep,
)


def get_schema_registry_metadata_service(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
) -> SchemaRegistryMetadataService:
    return SchemaRegistryMetadataService(
        data_source_service=data_source_service,
        object_service=object_service,
    )


SchemaRegistryMetadataServiceDep = Annotated[
    SchemaRegistryMetadataService,
    Depends(get_schema_registry_metadata_service),
]


def get_schema_diff_service() -> SchemaDiffService:
    return SchemaDiffService()


SchemaDiffServiceDep = Annotated[
    SchemaDiffService,
    Depends(get_schema_diff_service),
]


__all__ = [
    "SchemaDiffServiceDep",
    "SchemaRegistryMetadataServiceDep",
    "get_schema_diff_service",
    "get_schema_registry_metadata_service",
]
