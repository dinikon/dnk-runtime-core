from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.broadcast.application.broadcast.repository import (
    BroadcastCommandRepositoryProtocol,
    BroadcastQueryRepositoryProtocol,
)
from src.modules.broadcast.application.broadcast.query import (
    BroadcastFieldsDescriptionRepositoryProtocol,
)
from src.modules.broadcast.infrastructure import (
    BroadcastModelDescriptionRepository,
    BroadcastRuntimeRepository,
)
from src.modules.runtime_data.application.query.capabilities.query_capability_resolver import (
    QueryCapabilityResolver,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.presentation.depends.application import (
    DescribeRuntimeObjectUseCaseDep,
    RuntimeObjectResolverDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для broadcast gateway."""
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_query_capability_resolver() -> QueryCapabilityResolver:
    """Создает resolver query capabilities для broadcast fields metadata."""
    return QueryCapabilityResolver()


QueryCapabilityResolverDep = Annotated[
    QueryCapabilityResolver,
    Depends(get_query_capability_resolver),
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


def get_broadcast_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> BroadcastCommandRepositoryProtocol:
    """Создает command repository broadcast поверх runtime gateway."""
    return BroadcastRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


def get_broadcast_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> BroadcastQueryRepositoryProtocol:
    """Создает query repository broadcast поверх runtime gateway."""
    return BroadcastRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


BroadcastCommandRepositoryDep = Annotated[
    BroadcastCommandRepositoryProtocol,
    Depends(get_broadcast_command_repository),
]

BroadcastQueryRepositoryDep = Annotated[
    BroadcastQueryRepositoryProtocol,
    Depends(get_broadcast_query_repository),
]


def get_broadcast_fields_description_repository(
    describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseDep,
    runtime_object_resolver: RuntimeObjectResolverDep,
    query_capability_resolver: QueryCapabilityResolverDep,
) -> BroadcastFieldsDescriptionRepositoryProtocol:
    """Создает repository описания модели broadcast через schema_registry."""
    return BroadcastModelDescriptionRepository(
        describe_runtime_object_use_case=describe_runtime_object_use_case,
        runtime_object_resolver=runtime_object_resolver,
        query_capability_resolver=query_capability_resolver,
    )


BroadcastFieldsDescriptionRepositoryDep = Annotated[
    BroadcastFieldsDescriptionRepositoryProtocol,
    Depends(get_broadcast_fields_description_repository),
]


__all__ = [
    "BroadcastCommandRepositoryDep",
    "BroadcastFieldsDescriptionRepositoryDep",
    "BroadcastQueryRepositoryDep",
    "QueryCapabilityResolverDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "get_broadcast_command_repository",
    "get_broadcast_fields_description_repository",
    "get_broadcast_query_repository",
    "get_query_capability_resolver",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
]
