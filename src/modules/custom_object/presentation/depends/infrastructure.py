from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application import CustomObjectStoreProtocol
from src.modules.custom_object.infrastructure import SchemaRegistryCustomObjectStore
from src.modules.runtime_data import PostgresRuntimeGateway, RuntimeFieldTypePolicy
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
from src.modules.shared.depends.uow import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для custom_object."""
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeGateway:
    """Создает PostgreSQL runtime gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeGatewayDep = Annotated[
    PostgresRuntimeGateway,
    Depends(get_runtime_gateway),
]


def get_custom_object_store(
    object_repository: ObjectRepositoryDep,
    data_source_service: DataSourceServiceDep,
    tenant_schema_executor: TenantSchemaExecutorDep,
    postgres_field_canonicalizer: PostgresFieldCanonicalizerDep,
    field_type_catalog: FieldTypeCatalogDep,
    clock: ClockDep,
) -> CustomObjectStoreProtocol:
    """Создает custom-object store поверх schema_registry и DDL executor."""
    return SchemaRegistryCustomObjectStore(
        object_repository=object_repository,
        data_source_service=data_source_service,
        tenant_schema_executor=tenant_schema_executor,
        postgres_field_canonicalizer=postgres_field_canonicalizer,
        field_type_catalog=field_type_catalog,
        clock=clock,
        object_id_provider=get_runtime_object_id_provider(),
        field_id_provider=get_runtime_field_id_provider(),
    )


CustomObjectStoreDep = Annotated[
    CustomObjectStoreProtocol,
    Depends(get_custom_object_store),
]


__all__ = [
    "CustomObjectStoreDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeGatewayDep",
    "get_custom_object_store",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
