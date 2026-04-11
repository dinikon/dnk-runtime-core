from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.application.metadata.schema_registry_metadata_read_service import (
    SchemaRegistryMetadataReadService,
)
from src.modules.schema_registry.application.metadata.schema_registry_metadata_write_service import (
    SchemaRegistryMetadataWriteService,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
)
from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.schema_registry.application.use_case.diff_schema_use_case import (
    DiffSchemaUseCase,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectResolverProtocol,
    SchemaRegistryRuntimeObjectResolver,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep,
    FieldTypeCatalogDep,
    ObjectServiceDep,
    PostgresFieldCanonicalizerDep,
    SchemaSeedReaderDep,
    TenantSchemaExecutorDep,
    TenantSchemaInspectorDep,
)


def get_schema_seed_service(
    seed_reader: SchemaSeedReaderDep,
    field_type_catalog: FieldTypeCatalogDep,
) -> SchemaSeedService:
    return SchemaSeedService(
        seed_reader=seed_reader,
        field_type_catalog=field_type_catalog,
    )


SchemaSeedServiceDep = Annotated[
    SchemaSeedService,
    Depends(get_schema_seed_service),
]


def get_postgres_schema_service(
    inspector: TenantSchemaInspectorDep,
    executor: TenantSchemaExecutorDep,
) -> PostgresSchemaService:
    return PostgresSchemaService(
        inspector=inspector,
        executor=executor,
    )


PostgresSchemaServiceDep = Annotated[
    PostgresSchemaService,
    Depends(get_postgres_schema_service),
]


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


def get_postgres_schema_plan_service(
    field_type_catalog: FieldTypeCatalogDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
) -> PostgresSchemaPlanService:
    return PostgresSchemaPlanService(
        field_type_catalog=field_type_catalog,
        postgres_field_canonicalizer=postgres_field_canonicalizer,
    )


PostgresSchemaPlanServiceDep = Annotated[
    PostgresSchemaPlanService,
    Depends(get_postgres_schema_plan_service),
]


def get_create_schema_use_case(
    schema_seed_service: SchemaSeedServiceDep,
    schema_plan_service: PostgresSchemaPlanServiceDep,
    postgres_schema_service: PostgresSchemaServiceDep,
    schema_registry_metadata_write_service: SchemaRegistryMetadataWriteServiceDep,
) -> CreateSchemaUseCase:
    return CreateSchemaUseCase(
        schema_seed_service=schema_seed_service,
        schema_plan_service=schema_plan_service,
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_write_service=schema_registry_metadata_write_service,
    )


CreateSchemaUseCaseDep = Annotated[
    CreateSchemaUseCase,
    Depends(get_create_schema_use_case),
]


def get_diff_schema_use_case(
    schema_seed_service: SchemaSeedServiceDep,
    schema_registry_metadata_read_service: SchemaRegistryMetadataReadServiceDep,
    schema_plan_service: PostgresSchemaPlanServiceDep,
    postgres_schema_service: PostgresSchemaServiceDep,
    schema_registry_metadata_write_service: SchemaRegistryMetadataWriteServiceDep,
) -> DiffSchemaUseCase:
    return DiffSchemaUseCase(
        schema_seed_service=schema_seed_service,
        schema_registry_metadata_read_service=schema_registry_metadata_read_service,
        schema_plan_service=schema_plan_service,
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_write_service=schema_registry_metadata_write_service,
    )


DiffSchemaUseCaseDep = Annotated[
    DiffSchemaUseCase,
    Depends(get_diff_schema_use_case),
]


def get_runtime_object_resolver(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
) -> RuntimeObjectResolverProtocol:
    return SchemaRegistryRuntimeObjectResolver(
        data_source_service=data_source_service,
        object_service=object_service,
    )


RuntimeObjectResolverDep = Annotated[
    RuntimeObjectResolverProtocol,
    Depends(get_runtime_object_resolver),
]


__all__ = [
    "CreateSchemaUseCaseDep",
    "DiffSchemaUseCaseDep",
    "PostgresSchemaServiceDep",
    "PostgresSchemaPlanServiceDep",
    "RuntimeObjectResolverDep",
    "SchemaSeedServiceDep",
    "SchemaRegistryMetadataReadServiceDep",
    "SchemaRegistryMetadataWriteServiceDep",
    "get_create_schema_use_case",
    "get_diff_schema_use_case",
    "get_postgres_schema_service",
    "get_postgres_schema_plan_service",
    "get_schema_registry_metadata_read_service",
    "get_schema_registry_metadata_write_service",
    "get_runtime_object_resolver",
    "get_schema_seed_service",
]
