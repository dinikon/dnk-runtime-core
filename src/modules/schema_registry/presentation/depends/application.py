from __future__ import annotations

from typing import Annotated, TypeAlias

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
from src.modules.schema_registry.application.object_feature.use_case import (
    AssertObjectFeatureEnabledUseCase,
    DisableObjectFeatureUseCase,
    EnableObjectFeatureUseCase,
    GetObjectFeatureConfigUseCase,
)
from src.modules.schema_registry.application.service.postgres_schema_service import (
    PostgresSchemaService,
)
from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.application.use_case.describe_runtime_object_use_case import (
    DescribeRuntimeObjectUseCase,
    DescribeRuntimeObjectUseCaseProtocol,
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
    ObjectFeatureConfigRepositoryDep,
    ObjectServiceDep,
    PostgresFieldCanonicalizerDep,
    RelationServiceDep,
    SchemaSeedReaderDep,
    TenantSchemaExecutorDep,
    TenantSchemaInspectorDep,
    get_object_feature_config_id_provider,
)
from src.modules.shared.depends import ClockDep


def get_schema_seed_service(
    seed_reader: SchemaSeedReaderDep,
    field_type_catalog: FieldTypeCatalogDep,
) -> SchemaSeedService:
    """Создает application service для загрузки и нормализации seed."""
    return SchemaSeedService(
        seed_reader=seed_reader,
        field_type_catalog=field_type_catalog,
    )


SchemaSeedServiceDep: TypeAlias = Annotated[
    SchemaSeedService,
    Depends(get_schema_seed_service),
]


def get_postgres_schema_service(
    inspector: TenantSchemaInspectorDep,
    executor: TenantSchemaExecutorDep,
) -> PostgresSchemaService:
    """Создает сервис работы с физической PostgreSQL-схемой."""
    return PostgresSchemaService(
        inspector=inspector,
        executor=executor,
    )


PostgresSchemaServiceDep: TypeAlias = Annotated[
    PostgresSchemaService,
    Depends(get_postgres_schema_service),
]


def get_schema_registry_metadata_read_service(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
    relation_service: RelationServiceDep,
) -> SchemaRegistryMetadataReadService:
    """Создает сервис чтения metadata schema_registry."""
    return SchemaRegistryMetadataReadService(
        data_source_service=data_source_service,
        object_service=object_service,
        relation_service=relation_service,
    )


SchemaRegistryMetadataReadServiceDep: TypeAlias = Annotated[
    SchemaRegistryMetadataReadService,
    Depends(get_schema_registry_metadata_read_service),
]


def get_schema_registry_metadata_write_service(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
    relation_service: RelationServiceDep,
) -> SchemaRegistryMetadataWriteService:
    """Создает сервис записи metadata schema_registry."""
    return SchemaRegistryMetadataWriteService(
        data_source_service=data_source_service,
        object_service=object_service,
        relation_service=relation_service,
    )


SchemaRegistryMetadataWriteServiceDep: TypeAlias = Annotated[
    SchemaRegistryMetadataWriteService,
    Depends(get_schema_registry_metadata_write_service),
]


def get_postgres_schema_plan_service(
    field_type_catalog: FieldTypeCatalogDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
) -> PostgresSchemaPlanService:
    """Создает сервис построения PostgreSQL migration plan."""
    return PostgresSchemaPlanService(
        field_type_catalog=field_type_catalog,
        postgres_field_canonicalizer=postgres_field_canonicalizer,
    )


PostgresSchemaPlanServiceDep: TypeAlias = Annotated[
    PostgresSchemaPlanService,
    Depends(get_postgres_schema_plan_service),
]


def get_create_schema_use_case(
    schema_seed_service: SchemaSeedServiceDep,
    schema_plan_service: PostgresSchemaPlanServiceDep,
    postgres_schema_service: PostgresSchemaServiceDep,
    schema_registry_metadata_write_service: SchemaRegistryMetadataWriteServiceDep,
) -> CreateSchemaUseCase:
    """Создает use case первичного создания runtime-схемы."""
    return CreateSchemaUseCase(
        schema_seed_service=schema_seed_service,
        schema_plan_service=schema_plan_service,
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_write_service=schema_registry_metadata_write_service,
    )


CreateSchemaUseCaseDep: TypeAlias = Annotated[
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
    """Создает use case применения diff к runtime-схеме."""
    return DiffSchemaUseCase(
        schema_seed_service=schema_seed_service,
        schema_registry_metadata_read_service=schema_registry_metadata_read_service,
        schema_plan_service=schema_plan_service,
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_write_service=schema_registry_metadata_write_service,
    )


DiffSchemaUseCaseDep: TypeAlias = Annotated[
    DiffSchemaUseCase,
    Depends(get_diff_schema_use_case),
]


def get_describe_runtime_object_use_case(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
    relation_service: RelationServiceDep,
) -> DescribeRuntimeObjectUseCaseProtocol:
    """Создает use case чтения описания runtime-объекта tenant."""
    return DescribeRuntimeObjectUseCase(
        data_source_service=data_source_service,
        object_service=object_service,
        relation_service=relation_service,
    )


DescribeRuntimeObjectUseCaseDep: TypeAlias = Annotated[
    DescribeRuntimeObjectUseCaseProtocol,
    Depends(get_describe_runtime_object_use_case),
]


def get_runtime_object_resolver(
    data_source_service: DataSourceServiceDep,
    object_service: ObjectServiceDep,
    relation_service: RelationServiceDep,
) -> RuntimeObjectResolverProtocol:
    """Создает resolver runtime descriptor из metadata schema_registry."""
    return SchemaRegistryRuntimeObjectResolver(
        data_source_service=data_source_service,
        object_service=object_service,
        relation_service=relation_service,
    )


RuntimeObjectResolverDep: TypeAlias = Annotated[
    RuntimeObjectResolverProtocol,
    Depends(get_runtime_object_resolver),
]


def get_enable_object_feature_use_case(
    repository: ObjectFeatureConfigRepositoryDep,
    clock: ClockDep,
) -> EnableObjectFeatureUseCase:
    """Создает use case включения object feature config."""
    return EnableObjectFeatureUseCase(
        repository=repository,
        clock=clock,
        id_provider=get_object_feature_config_id_provider(),
    )


EnableObjectFeatureUseCaseDep: TypeAlias = Annotated[
    EnableObjectFeatureUseCase,
    Depends(get_enable_object_feature_use_case),
]


def get_disable_object_feature_use_case(
    repository: ObjectFeatureConfigRepositoryDep,
    clock: ClockDep,
) -> DisableObjectFeatureUseCase:
    """Создает use case выключения object feature config."""
    return DisableObjectFeatureUseCase(repository=repository, clock=clock)


DisableObjectFeatureUseCaseDep: TypeAlias = Annotated[
    DisableObjectFeatureUseCase,
    Depends(get_disable_object_feature_use_case),
]


def get_get_object_feature_config_use_case(
    repository: ObjectFeatureConfigRepositoryDep,
) -> GetObjectFeatureConfigUseCase:
    """Создает use case чтения object feature config."""
    return GetObjectFeatureConfigUseCase(repository)


GetObjectFeatureConfigUseCaseDep: TypeAlias = Annotated[
    GetObjectFeatureConfigUseCase,
    Depends(get_get_object_feature_config_use_case),
]


def get_assert_object_feature_enabled_use_case(
    repository: ObjectFeatureConfigRepositoryDep,
) -> AssertObjectFeatureEnabledUseCase:
    """Создает use case проверки enabled-статуса object feature."""
    return AssertObjectFeatureEnabledUseCase(repository)


AssertObjectFeatureEnabledUseCaseDep: TypeAlias = Annotated[
    AssertObjectFeatureEnabledUseCase,
    Depends(get_assert_object_feature_enabled_use_case),
]


__all__ = [
    "AssertObjectFeatureEnabledUseCaseDep",
    "CreateSchemaUseCaseDep",
    "DescribeRuntimeObjectUseCaseDep",
    "DisableObjectFeatureUseCaseDep",
    "DiffSchemaUseCaseDep",
    "EnableObjectFeatureUseCaseDep",
    "GetObjectFeatureConfigUseCaseDep",
    "PostgresSchemaServiceDep",
    "PostgresSchemaPlanServiceDep",
    "RuntimeObjectResolverDep",
    "SchemaSeedServiceDep",
    "SchemaRegistryMetadataReadServiceDep",
    "SchemaRegistryMetadataWriteServiceDep",
    "get_assert_object_feature_enabled_use_case",
    "get_create_schema_use_case",
    "get_describe_runtime_object_use_case",
    "get_disable_object_feature_use_case",
    "get_diff_schema_use_case",
    "get_enable_object_feature_use_case",
    "get_get_object_feature_config_use_case",
    "get_postgres_schema_service",
    "get_postgres_schema_plan_service",
    "get_schema_registry_metadata_read_service",
    "get_schema_registry_metadata_write_service",
    "get_runtime_object_resolver",
    "get_schema_seed_service",
]
