from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.contact_point.infrastructure import (
    ContactPointHashService,
    ContactPointNormalizeService,
    ContactPointRuntimeRepository,
    RuntimeOwnerResolver,
    SchemaRegistryContactPointObjectFeatureGate,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.presentation.depends.application import (
    AssertObjectFeatureEnabledUseCaseDep,
    RuntimeObjectResolverDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_query_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeQueryGateway:
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
    return PostgresRuntimeCommandGateway(
        uow.session,
        type_policy=type_policy,
        query_gateway=runtime_query_gateway,
    )


RuntimeCommandGatewayDep = Annotated[
    PostgresRuntimeCommandGateway,
    Depends(get_runtime_command_gateway),
]


def get_contact_point_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> ContactPointRuntimeRepository:
    return ContactPointRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


ContactPointRuntimeRepositoryDep = Annotated[
    ContactPointRuntimeRepository,
    Depends(get_contact_point_repository),
]


def get_owner_resolver(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> RuntimeOwnerResolver:
    return RuntimeOwnerResolver(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_query_gateway,
    )


OwnerResolverDep = Annotated[
    RuntimeOwnerResolver,
    Depends(get_owner_resolver),
]


def get_contact_point_object_feature_gate(
    assert_object_feature_enabled: AssertObjectFeatureEnabledUseCaseDep,
) -> SchemaRegistryContactPointObjectFeatureGate:
    return SchemaRegistryContactPointObjectFeatureGate(
        assert_object_feature_enabled=assert_object_feature_enabled,
    )


ContactPointObjectFeatureGateDep = Annotated[
    SchemaRegistryContactPointObjectFeatureGate,
    Depends(get_contact_point_object_feature_gate),
]


def get_contact_point_normalizer() -> ContactPointNormalizeService:
    return ContactPointNormalizeService()


ContactPointNormalizerDep = Annotated[
    ContactPointNormalizeService,
    Depends(get_contact_point_normalizer),
]


def get_contact_point_hash_service() -> ContactPointHashService:
    return ContactPointHashService()


ContactPointHashServiceDep = Annotated[
    ContactPointHashService,
    Depends(get_contact_point_hash_service),
]


__all__ = [
    "ContactPointHashServiceDep",
    "ContactPointNormalizerDep",
    "ContactPointObjectFeatureGateDep",
    "ContactPointRuntimeRepositoryDep",
    "OwnerResolverDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "get_contact_point_hash_service",
    "get_contact_point_normalizer",
    "get_contact_point_object_feature_gate",
    "get_contact_point_repository",
    "get_owner_resolver",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
]
