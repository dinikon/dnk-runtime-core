from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.service.schema_registry_metadata_read_service import (
    SchemaRegistryMetadataReadService,
)
from src.modules.schema_registry.domain.service.schema_registry_metadata_write_service import (
    SchemaRegistryMetadataWriteService,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep,
    FieldTypeServiceDep,
    ObjectServiceDep,
)


def get_schema_registry_metadata_read_service(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
) -> SchemaRegistryMetadataReadService:
    return SchemaRegistryMetadataReadService(
        data_source_service=data_source_service,
        object_service=object_service,
    )


SchemaRegistryMetadataReadServiceDep = Annotated[
    SchemaRegistryMetadataReadService,
    Depends(get_schema_registry_metadata_read_service),
]


def get_schema_registry_metadata_write_service(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
) -> SchemaRegistryMetadataWriteService:
    return SchemaRegistryMetadataWriteService(
        data_source_service=data_source_service,
        object_service=object_service,
    )


SchemaRegistryMetadataWriteServiceDep = Annotated[
    SchemaRegistryMetadataWriteService,
    Depends(get_schema_registry_metadata_write_service),
]


def get_schema_diff_service(
    field_type_service: FieldTypeServiceDep,
) -> SchemaDiffService:
    return SchemaDiffService(field_type_service=field_type_service)


SchemaDiffServiceDep = Annotated[
    SchemaDiffService,
    Depends(get_schema_diff_service),
]


__all__ = [
    "SchemaDiffServiceDep",
    "SchemaRegistryMetadataReadServiceDep",
    "SchemaRegistryMetadataWriteServiceDep",
    "get_schema_diff_service",
    "get_schema_registry_metadata_read_service",
    "get_schema_registry_metadata_write_service",
]
