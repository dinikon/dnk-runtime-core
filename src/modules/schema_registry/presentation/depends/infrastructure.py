from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import uuid6
from fastapi import Depends

from src.modules.shared import EntityIdVO
from src.modules.shared.depends.clock import ClockDep
from src.modules.shared.depends.uow import UoWDep
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.domain.datasource.repository import (
    DataSourceRepositoryProtocol,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.object.repository import (
    ObjectRepositoryProtocol,
)
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.infrastructure.postgres.tenant_schema_executor import (
    PostgresTenantSchemaExecutor,
)
from src.modules.schema_registry.infrastructure.postgres.tenant_schema_inspector import (
    PostgresTenantSchemaInspector,
)
from src.modules.schema_registry.infrastructure.repository.data_source_repository import (
    SqlAlchemyDataSourceRepository,
)
from src.modules.schema_registry.infrastructure.repository.object_repository import (
    SqlAlchemyObjectRepository,
)
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)


def get_schema_seed_reader() -> SeedReaderPort:
    return PythonModuleSeedReader()


SchemaSeedReaderDep = Annotated[
    SeedReaderPort,
    Depends(get_schema_seed_reader),
]


def get_tenant_schema_inspector(
    uow: UoWDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
) -> TenantSchemaInspectorPort:
    return PostgresTenantSchemaInspector(uow.session, postgres_field_canonicalizer)


TenantSchemaInspectorDep = Annotated[
    TenantSchemaInspectorPort,
    Depends(get_tenant_schema_inspector),
]


def get_tenant_schema_executor(
    uow: UoWDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
) -> TenantSchemaExecutorPort:
    return PostgresTenantSchemaExecutor(uow.session, postgres_field_canonicalizer)


TenantSchemaExecutorDep = Annotated[
    TenantSchemaExecutorPort,
    Depends(get_tenant_schema_executor),
]


def get_data_source_repository(uow: UoWDep) -> DataSourceRepositoryProtocol:
    return SqlAlchemyDataSourceRepository(uow.session)


DataSourceRepositoryDep = Annotated[
    DataSourceRepositoryProtocol,
    Depends(get_data_source_repository),
]


def get_object_repository(uow: UoWDep) -> ObjectRepositoryProtocol:
    return SqlAlchemyObjectRepository(uow.session)


ObjectRepositoryDep = Annotated[
    ObjectRepositoryProtocol,
    Depends(get_object_repository),
]


def get_entity_id_provider() -> Callable[[], EntityIdVO]:
    return lambda: EntityIdVO.from_value(uuid6.uuid7())


def get_field_type_catalog() -> FieldTypeCatalog:
    return FieldTypeCatalog()


FieldTypeCatalogDep = Annotated[
    FieldTypeCatalog,
    Depends(get_field_type_catalog),
]


def get_postgres_field_canonicalizer() -> PostgresFieldCanonicalizer:
    return PostgresFieldCanonicalizer()


PostgresFieldCanonicalizerDep = Annotated[
    PostgresFieldCanonicalizer,
    Depends(get_postgres_field_canonicalizer),
]


def get_data_source_service(
    repository: DataSourceRepositoryDep,
    clock: ClockDep,
) -> DataSourceService:
    return DataSourceService(
        repository=repository,
        clock=clock,
        id_provider=get_entity_id_provider(),
    )


DataSourceServiceDep = Annotated[
    DataSourceService,
    Depends(get_data_source_service),
]


def get_object_service(
    repository: ObjectRepositoryDep,
    clock: ClockDep,
    field_type_catalog: FieldTypeCatalogDep,
) -> ObjectService:
    return ObjectService(
        object_repository=repository,
        clock=clock,
        id_provider=get_entity_id_provider(),
        field_type_catalog=field_type_catalog,
    )


ObjectServiceDep = Annotated[
    ObjectService,
    Depends(get_object_service),
]


__all__ = [
    "DataSourceRepositoryDep",
    "DataSourceServiceDep",
    "ObjectRepositoryDep",
    "ObjectServiceDep",
    "FieldTypeCatalogDep",
    "PostgresFieldCanonicalizerDep",
    "SchemaSeedReaderDep",
    "TenantSchemaExecutorDep",
    "TenantSchemaInspectorDep",
    "get_data_source_repository",
    "get_data_source_service",
    "get_object_repository",
    "get_object_service",
    "get_field_type_catalog",
    "get_postgres_field_canonicalizer",
    "get_schema_seed_reader",
    "get_tenant_schema_executor",
    "get_tenant_schema_inspector",
]
