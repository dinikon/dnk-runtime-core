from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)
from src.modules.custom_object.infrastructure import CustomRecordRuntimeRepository
from src.modules.runtime_data import PostgresRuntimeGateway, RuntimeFieldTypePolicy
from src.modules.schema_registry.presentation.depends.application import (
    RuntimeObjectResolverDep,
)
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


def get_custom_record_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CustomRecordRepositoryProtocol:
    """Создает custom-object record repository поверх runtime gateway."""
    return CustomRecordRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        command_gateway=runtime_gateway,
        query_gateway=runtime_gateway,
    )


CustomRecordRepositoryDep = Annotated[
    CustomRecordRepositoryProtocol,
    Depends(get_custom_record_repository),
]


__all__ = [
    "CustomRecordRepositoryDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeGatewayDep",
    "get_custom_record_repository",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
