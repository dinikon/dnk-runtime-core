from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)
from src.modules.custom_object.infrastructure import CustomRecordRuntimeRepository
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.presentation.depends.application import (
    RuntimeObjectResolverDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для custom_object."""
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_query_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeQueryGateway:
    """Создает PostgreSQL runtime query gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeQueryGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeQueryGatewayDep = Annotated[
    PostgresRuntimeQueryGateway,
    Depends(get_runtime_query_gateway),
]


def get_runtime_command_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> PostgresRuntimeCommandGateway:
    """Создает PostgreSQL runtime command gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeCommandGateway(
        uow.session,
        type_policy=type_policy,
        query_gateway=runtime_query_gateway,
    )


RuntimeCommandGatewayDep = Annotated[
    PostgresRuntimeCommandGateway,
    Depends(get_runtime_command_gateway),
]


def get_custom_record_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> CustomRecordRepositoryProtocol:
    """Создает custom-object record repository поверх runtime gateway."""
    return CustomRecordRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        command_gateway=runtime_command_gateway,
        query_gateway=runtime_query_gateway,
    )


CustomRecordRepositoryDep = Annotated[
    CustomRecordRepositoryProtocol,
    Depends(get_custom_record_repository),
]


__all__ = [
    "CustomRecordRepositoryDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "get_custom_record_repository",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
]
