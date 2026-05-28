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
from src.modules.schema_registry.presentation.depends.infrastructure import (
    ObjectServiceDep,
)
from src.modules.segmentation.infrastructure import (
    RuntimeContactAudienceQuery,
    RuntimeContactLookupAdapter,
    RuntimeFilterValidatorAdapter,
    RuntimeObjectMetadataAdapter,
    SegmentDefinitionRuntimeRepository,
    SegmentStaticMemberRuntimeRepository,
    SegmentSnapshotMemberRuntimeRepository,
    SegmentSnapshotRuntimeRepository,
    SegmentVersionRuntimeRepository,
    StaticContactAudienceRuntimeQuery,
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


def get_segment_snapshot_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> SegmentSnapshotRuntimeRepository:
    return SegmentSnapshotRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


SegmentSnapshotCommandRepositoryDep = Annotated[
    SegmentSnapshotRuntimeRepository,
    Depends(get_segment_snapshot_repository),
]
SegmentSnapshotQueryRepositoryDep = Annotated[
    SegmentSnapshotRuntimeRepository,
    Depends(get_segment_snapshot_repository),
]


def get_segment_snapshot_member_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> SegmentSnapshotMemberRuntimeRepository:
    return SegmentSnapshotMemberRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


SegmentSnapshotMemberCommandRepositoryDep = Annotated[
    SegmentSnapshotMemberRuntimeRepository,
    Depends(get_segment_snapshot_member_repository),
]
SegmentSnapshotMemberQueryRepositoryDep = Annotated[
    SegmentSnapshotMemberRuntimeRepository,
    Depends(get_segment_snapshot_member_repository),
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


def get_contact_audience_query(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> RuntimeContactAudienceQuery:
    return RuntimeContactAudienceQuery(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_query_gateway,
    )


ContactAudienceQueryDep = Annotated[
    RuntimeContactAudienceQuery,
    Depends(get_contact_audience_query),
]


def get_static_contact_audience_query(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> StaticContactAudienceRuntimeQuery:
    return StaticContactAudienceRuntimeQuery(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_query_gateway,
    )


StaticContactAudienceQueryDep = Annotated[
    StaticContactAudienceRuntimeQuery,
    Depends(get_static_contact_audience_query),
]


def get_runtime_object_metadata(
    runtime_object_resolver: RuntimeObjectResolverDep,
    object_service: ObjectServiceDep,
) -> RuntimeObjectMetadataAdapter:
    return RuntimeObjectMetadataAdapter(
        runtime_object_resolver=runtime_object_resolver,
        object_service=object_service,
    )


RuntimeObjectMetadataDep = Annotated[
    RuntimeObjectMetadataAdapter,
    Depends(get_runtime_object_metadata),
]


def get_runtime_filter_validator(
    runtime_object_resolver: RuntimeObjectResolverDep,
) -> RuntimeFilterValidatorAdapter:
    return RuntimeFilterValidatorAdapter(
        runtime_object_resolver=runtime_object_resolver,
    )


RuntimeFilterValidatorDep = Annotated[
    RuntimeFilterValidatorAdapter,
    Depends(get_runtime_filter_validator),
]


__all__ = [
    "ContactAudienceQueryDep",
    "ContactLookupDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFilterValidatorDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeObjectMetadataDep",
    "RuntimeQueryGatewayDep",
    "SegmentDefinitionCommandRepositoryDep",
    "SegmentDefinitionQueryRepositoryDep",
    "SegmentStaticMemberCommandRepositoryDep",
    "SegmentStaticMemberQueryRepositoryDep",
    "SegmentSnapshotCommandRepositoryDep",
    "SegmentSnapshotMemberCommandRepositoryDep",
    "SegmentSnapshotMemberQueryRepositoryDep",
    "SegmentSnapshotQueryRepositoryDep",
    "SegmentVersionCommandRepositoryDep",
    "SegmentVersionQueryRepositoryDep",
    "StaticContactAudienceQueryDep",
    "get_contact_audience_query",
    "get_contact_lookup",
    "get_runtime_filter_validator",
    "get_runtime_object_metadata",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
    "get_segment_definition_repository",
    "get_segment_static_member_repository",
    "get_segment_snapshot_member_repository",
    "get_segment_snapshot_repository",
    "get_segment_version_repository",
    "get_static_contact_audience_query",
]
