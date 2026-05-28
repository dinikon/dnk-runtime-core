from __future__ import annotations

from typing import Annotated

from fastapi import Depends

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
from src.modules.segmentation.infrastructure import (
    RuntimeContactLookupAdapter,
    SegmentDefinitionRuntimeRepository,
    SegmentStaticMemberRuntimeRepository,
    SegmentVersionRuntimeRepository,
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


def get_segment_definition_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> SegmentDefinitionRuntimeRepository:
    return SegmentDefinitionRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


SegmentDefinitionCommandRepositoryDep = Annotated[
    SegmentDefinitionRuntimeRepository,
    Depends(get_segment_definition_repository),
]
SegmentDefinitionQueryRepositoryDep = Annotated[
    SegmentDefinitionRuntimeRepository,
    Depends(get_segment_definition_repository),
]


def get_segment_static_member_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> SegmentStaticMemberRuntimeRepository:
    return SegmentStaticMemberRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


SegmentStaticMemberCommandRepositoryDep = Annotated[
    SegmentStaticMemberRuntimeRepository,
    Depends(get_segment_static_member_repository),
]
SegmentStaticMemberQueryRepositoryDep = Annotated[
    SegmentStaticMemberRuntimeRepository,
    Depends(get_segment_static_member_repository),
]


def get_segment_version_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> SegmentVersionRuntimeRepository:
    return SegmentVersionRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


SegmentVersionCommandRepositoryDep = Annotated[
    SegmentVersionRuntimeRepository,
    Depends(get_segment_version_repository),
]
SegmentVersionQueryRepositoryDep = Annotated[
    SegmentVersionRuntimeRepository,
    Depends(get_segment_version_repository),
]


def get_contact_lookup(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> RuntimeContactLookupAdapter:
    return RuntimeContactLookupAdapter(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_query_gateway,
    )


ContactLookupDep = Annotated[
    RuntimeContactLookupAdapter,
    Depends(get_contact_lookup),
]


__all__ = [
    "ContactLookupDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "SegmentDefinitionCommandRepositoryDep",
    "SegmentDefinitionQueryRepositoryDep",
    "SegmentStaticMemberCommandRepositoryDep",
    "SegmentStaticMemberQueryRepositoryDep",
    "SegmentVersionCommandRepositoryDep",
    "SegmentVersionQueryRepositoryDep",
    "get_contact_lookup",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
    "get_segment_definition_repository",
    "get_segment_static_member_repository",
    "get_segment_version_repository",
]
