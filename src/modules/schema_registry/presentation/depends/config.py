from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.schema_registry.application.config.field.repository import (
    SchemaConfigFieldRepositoryProtocol,
)
from src.modules.schema_registry.application.config.field.use_case import (
    AddCustomFieldUseCase,
    DeleteCustomFieldUseCase,
)
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)
from src.modules.schema_registry.application.config.object.use_case import (
    CreateCustomObjectUseCase,
    DeleteCustomObjectUseCase,
    DescribeCustomObjectUseCase,
    ListCustomObjectsUseCase,
)
from src.modules.schema_registry.infrastructure.config.schema_config_repository import (
    SchemaConfigRepository,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep,
    FieldTypeCatalogDep,
    ObjectRepositoryDep,
    PostgresFieldCanonicalizerDep,
    TenantSchemaExecutorDep,
    get_runtime_field_id_provider,
    get_runtime_object_id_provider,
)
from src.modules.shared.depends import ClockDep


def get_schema_config_repository(
    object_repository: ObjectRepositoryDep,
    data_source_service: DataSourceServiceDep,
    tenant_schema_executor: TenantSchemaExecutorDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
    field_type_catalog: FieldTypeCatalogDep,
    clock: ClockDep,
) -> SchemaConfigRepositoryProtocol:
    """Создает schema config repository поверх schema_registry metadata и DDL."""
    return SchemaConfigRepository(
        object_repository=object_repository,
        data_source_service=data_source_service,
        tenant_schema_executor=tenant_schema_executor,
        postgres_field_canonicalizer=postgres_field_canonicalizer,
        field_type_catalog=field_type_catalog,
        clock=clock,
        object_id_provider=get_runtime_object_id_provider(),
        field_id_provider=get_runtime_field_id_provider(),
    )


SchemaConfigRepositoryDep = Annotated[
    SchemaConfigRepositoryProtocol,
    Depends(get_schema_config_repository),
]

SchemaConfigFieldRepositoryDep = Annotated[
    SchemaConfigFieldRepositoryProtocol,
    Depends(get_schema_config_repository),
]


def get_list_custom_objects_use_case(
    repository: SchemaConfigRepositoryDep,
) -> ListCustomObjectsUseCase:
    """Создает use case списка runtime objects."""
    return ListCustomObjectsUseCase(repository)


ListCustomObjectsUseCaseDep = Annotated[
    ListCustomObjectsUseCase,
    Depends(get_list_custom_objects_use_case),
]


def get_create_custom_object_use_case(
    repository: SchemaConfigRepositoryDep,
) -> CreateCustomObjectUseCase:
    """Создает use case создания custom object."""
    return CreateCustomObjectUseCase(repository)


CreateCustomObjectUseCaseDep = Annotated[
    CreateCustomObjectUseCase,
    Depends(get_create_custom_object_use_case),
]


def get_describe_custom_object_use_case(
    repository: SchemaConfigRepositoryDep,
) -> DescribeCustomObjectUseCase:
    """Создает use case чтения runtime object schema."""
    return DescribeCustomObjectUseCase(repository)


DescribeCustomObjectUseCaseDep = Annotated[
    DescribeCustomObjectUseCase,
    Depends(get_describe_custom_object_use_case),
]


def get_delete_custom_object_use_case(
    repository: SchemaConfigRepositoryDep,
) -> DeleteCustomObjectUseCase:
    """Создает use case удаления custom object."""
    return DeleteCustomObjectUseCase(repository)


DeleteCustomObjectUseCaseDep = Annotated[
    DeleteCustomObjectUseCase,
    Depends(get_delete_custom_object_use_case),
]


def get_add_custom_field_use_case(
    repository: SchemaConfigFieldRepositoryDep,
) -> AddCustomFieldUseCase:
    """Создает use case добавления custom field."""
    return AddCustomFieldUseCase(repository)


AddCustomFieldUseCaseDep = Annotated[
    AddCustomFieldUseCase,
    Depends(get_add_custom_field_use_case),
]


def get_delete_custom_field_use_case(
    repository: SchemaConfigFieldRepositoryDep,
) -> DeleteCustomFieldUseCase:
    """Создает use case удаления custom field."""
    return DeleteCustomFieldUseCase(repository)


DeleteCustomFieldUseCaseDep = Annotated[
    DeleteCustomFieldUseCase,
    Depends(get_delete_custom_field_use_case),
]


__all__ = [
    "AddCustomFieldUseCaseDep",
    "CreateCustomObjectUseCaseDep",
    "DeleteCustomFieldUseCaseDep",
    "DeleteCustomObjectUseCaseDep",
    "DescribeCustomObjectUseCaseDep",
    "ListCustomObjectsUseCaseDep",
    "SchemaConfigFieldRepositoryDep",
    "SchemaConfigRepositoryDep",
    "get_add_custom_field_use_case",
    "get_create_custom_object_use_case",
    "get_delete_custom_field_use_case",
    "get_delete_custom_object_use_case",
    "get_describe_custom_object_use_case",
    "get_list_custom_objects_use_case",
    "get_schema_config_repository",
]
