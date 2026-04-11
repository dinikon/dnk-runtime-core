from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
)
from src.modules.crm.infrastructure import ContactRuntimeRepository
from src.modules.runtime_data import PostgresRuntimeGateway, RuntimeFieldTypePolicy
from src.modules.schema_registry.presentation.depends.application import (
    RuntimeObjectResolverDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeGateway:
    return PostgresRuntimeGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeGatewayDep = Annotated[
    PostgresRuntimeGateway,
    Depends(get_runtime_gateway),
]


def get_contact_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ContactQueryRepositoryProtocol:
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol,
    Depends(get_contact_query_repository),
]


def get_contact_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ContactCommandRepositoryProtocol:
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ContactCommandRepositoryDep = Annotated[
    ContactCommandRepositoryProtocol,
    Depends(get_contact_command_repository),
]


__all__ = [
    "ContactCommandRepositoryDep",
    "ContactQueryRepositoryDep",
    "RuntimeGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "get_contact_command_repository",
    "get_contact_query_repository",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]
