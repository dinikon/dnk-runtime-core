from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.use_case.create_schema_use_case import (
    CreateSchemaUseCase,
)
from src.modules.schema_registry.presentation.depends.domain import (
    SchemaDiffServiceDep,
    SchemaRegistryMetadataServiceDep,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    SchemaSeedReaderDep,
    TenantSchemaExecutorDep,
    TenantSchemaInspectorDep,
)


def get_schema_seed_service(seed_reader: SchemaSeedReaderDep) -> SchemaSeedService:
    return SchemaSeedService(seed_reader=seed_reader)


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


def get_create_schema_use_case(
    schema_seed_service: SchemaSeedServiceDep,
    schema_diff_service: SchemaDiffServiceDep,
    postgres_schema_service: PostgresSchemaServiceDep,
    schema_registry_metadata_service: SchemaRegistryMetadataServiceDep,
) -> CreateSchemaUseCase:
    return CreateSchemaUseCase(
        schema_seed_service=schema_seed_service,
        schema_diff_service=schema_diff_service,
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_service=schema_registry_metadata_service,
    )


CreateSchemaUseCaseDep = Annotated[
    CreateSchemaUseCase,
    Depends(get_create_schema_use_case),
]


__all__ = [
    "CreateSchemaUseCaseDep",
    "PostgresSchemaServiceDep",
    "SchemaSeedServiceDep",
    "get_create_schema_use_case",
    "get_postgres_schema_service",
    "get_schema_seed_service",
]
