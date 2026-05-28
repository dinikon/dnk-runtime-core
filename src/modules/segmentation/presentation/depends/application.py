from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.segmentation.application.segment_definition import (
    ArchiveSegmentDefinitionUseCase,
    CreateSegmentDefinitionUseCase,
    GetSegmentDefinitionUseCase,
    ListSegmentDefinitionsUseCase,
    UpdateSegmentDefinitionUseCase,
)
from src.modules.segmentation.application.segment_static_member import (
    AddStaticMemberUseCase,
    ListStaticMembersUseCase,
    RemoveStaticMemberUseCase,
)
from src.modules.segmentation.application.segment_version import (
    ActivateSegmentVersionUseCase,
    CreateSegmentVersionUseCase,
    GetSegmentVersionUseCase,
    ListSegmentVersionsUseCase,
    SegmentVersionDslConfigValidator,
)
from src.modules.segmentation.presentation.depends.infrastructure import (
    ContactLookupDep,
    RuntimeFilterValidatorDep,
    RuntimeObjectMetadataDep,
    SegmentDefinitionCommandRepositoryDep,
    SegmentDefinitionQueryRepositoryDep,
    SegmentStaticMemberCommandRepositoryDep,
    SegmentStaticMemberQueryRepositoryDep,
    SegmentVersionCommandRepositoryDep,
    SegmentVersionQueryRepositoryDep,
)
from src.modules.shared.presentation import ClockDep, UuidDep


def get_create_segment_definition_use_case(
    command_repository: SegmentDefinitionCommandRepositoryDep,
    query_repository: SegmentDefinitionQueryRepositoryDep,
    uuid_generator: UuidDep,
) -> CreateSegmentDefinitionUseCase:
    return CreateSegmentDefinitionUseCase(
        command_repository=command_repository,
        query_repository=query_repository,
        uuid_generator=uuid_generator,
    )


CreateSegmentDefinitionUseCaseDep = Annotated[
    CreateSegmentDefinitionUseCase,
    Depends(get_create_segment_definition_use_case),
]


def get_update_segment_definition_use_case(
    command_repository: SegmentDefinitionCommandRepositoryDep,
    query_repository: SegmentDefinitionQueryRepositoryDep,
) -> UpdateSegmentDefinitionUseCase:
    return UpdateSegmentDefinitionUseCase(
        command_repository=command_repository,
        query_repository=query_repository,
    )


UpdateSegmentDefinitionUseCaseDep = Annotated[
    UpdateSegmentDefinitionUseCase,
    Depends(get_update_segment_definition_use_case),
]


def get_archive_segment_definition_use_case(
    command_repository: SegmentDefinitionCommandRepositoryDep,
    query_repository: SegmentDefinitionQueryRepositoryDep,
    clock: ClockDep,
) -> ArchiveSegmentDefinitionUseCase:
    return ArchiveSegmentDefinitionUseCase(
        command_repository=command_repository,
        query_repository=query_repository,
        clock=clock,
    )


ArchiveSegmentDefinitionUseCaseDep = Annotated[
    ArchiveSegmentDefinitionUseCase,
    Depends(get_archive_segment_definition_use_case),
]


def get_get_segment_definition_use_case(
    repository: SegmentDefinitionQueryRepositoryDep,
) -> GetSegmentDefinitionUseCase:
    return GetSegmentDefinitionUseCase(repository=repository)


GetSegmentDefinitionUseCaseDep = Annotated[
    GetSegmentDefinitionUseCase,
    Depends(get_get_segment_definition_use_case),
]


def get_list_segment_definitions_use_case(
    repository: SegmentDefinitionQueryRepositoryDep,
) -> ListSegmentDefinitionsUseCase:
    return ListSegmentDefinitionsUseCase(repository=repository)


ListSegmentDefinitionsUseCaseDep = Annotated[
    ListSegmentDefinitionsUseCase,
    Depends(get_list_segment_definitions_use_case),
]


def get_add_static_member_use_case(
    segment_repository: SegmentDefinitionCommandRepositoryDep,
    member_command_repository: SegmentStaticMemberCommandRepositoryDep,
    member_query_repository: SegmentStaticMemberQueryRepositoryDep,
    contact_lookup: ContactLookupDep,
    uuid_generator: UuidDep,
) -> AddStaticMemberUseCase:
    return AddStaticMemberUseCase(
        segment_repository=segment_repository,
        member_command_repository=member_command_repository,
        member_query_repository=member_query_repository,
        contact_lookup=contact_lookup,
        uuid_generator=uuid_generator,
    )


AddStaticMemberUseCaseDep = Annotated[
    AddStaticMemberUseCase,
    Depends(get_add_static_member_use_case),
]


def get_remove_static_member_use_case(
    segment_repository: SegmentDefinitionCommandRepositoryDep,
    member_repository: SegmentStaticMemberCommandRepositoryDep,
) -> RemoveStaticMemberUseCase:
    return RemoveStaticMemberUseCase(
        segment_repository=segment_repository,
        member_repository=member_repository,
    )


RemoveStaticMemberUseCaseDep = Annotated[
    RemoveStaticMemberUseCase,
    Depends(get_remove_static_member_use_case),
]


def get_list_static_members_use_case(
    repository: SegmentStaticMemberQueryRepositoryDep,
    contact_lookup: ContactLookupDep,
) -> ListStaticMembersUseCase:
    return ListStaticMembersUseCase(
        repository=repository,
        contact_lookup=contact_lookup,
    )


ListStaticMembersUseCaseDep = Annotated[
    ListStaticMembersUseCase,
    Depends(get_list_static_members_use_case),
]


def get_segment_version_dsl_config_validator(
    metadata: RuntimeObjectMetadataDep,
    filter_validator: RuntimeFilterValidatorDep,
    segment_repository: SegmentDefinitionCommandRepositoryDep,
) -> SegmentVersionDslConfigValidator:
    return SegmentVersionDslConfigValidator(
        metadata=metadata,
        filter_validator=filter_validator,
        segment_definition_repository=segment_repository,
    )


SegmentVersionDslConfigValidatorDep = Annotated[
    SegmentVersionDslConfigValidator,
    Depends(get_segment_version_dsl_config_validator),
]


def get_create_segment_version_use_case(
    segment_repository: SegmentDefinitionCommandRepositoryDep,
    version_command_repository: SegmentVersionCommandRepositoryDep,
    version_query_repository: SegmentVersionQueryRepositoryDep,
    dsl_validator: SegmentVersionDslConfigValidatorDep,
    uuid_generator: UuidDep,
) -> CreateSegmentVersionUseCase:
    return CreateSegmentVersionUseCase(
        segment_repository=segment_repository,
        version_command_repository=version_command_repository,
        version_query_repository=version_query_repository,
        dsl_validator=dsl_validator,
        uuid_generator=uuid_generator,
    )


CreateSegmentVersionUseCaseDep = Annotated[
    CreateSegmentVersionUseCase,
    Depends(get_create_segment_version_use_case),
]


def get_activate_segment_version_use_case(
    segment_repository: SegmentDefinitionCommandRepositoryDep,
    version_command_repository: SegmentVersionCommandRepositoryDep,
    version_query_repository: SegmentVersionQueryRepositoryDep,
    dsl_validator: SegmentVersionDslConfigValidatorDep,
    clock: ClockDep,
) -> ActivateSegmentVersionUseCase:
    return ActivateSegmentVersionUseCase(
        segment_repository=segment_repository,
        version_command_repository=version_command_repository,
        version_query_repository=version_query_repository,
        dsl_validator=dsl_validator,
        clock=clock,
    )


ActivateSegmentVersionUseCaseDep = Annotated[
    ActivateSegmentVersionUseCase,
    Depends(get_activate_segment_version_use_case),
]


def get_get_segment_version_use_case(
    repository: SegmentVersionQueryRepositoryDep,
) -> GetSegmentVersionUseCase:
    return GetSegmentVersionUseCase(repository=repository)


GetSegmentVersionUseCaseDep = Annotated[
    GetSegmentVersionUseCase,
    Depends(get_get_segment_version_use_case),
]


def get_list_segment_versions_use_case(
    repository: SegmentVersionQueryRepositoryDep,
) -> ListSegmentVersionsUseCase:
    return ListSegmentVersionsUseCase(repository=repository)


ListSegmentVersionsUseCaseDep = Annotated[
    ListSegmentVersionsUseCase,
    Depends(get_list_segment_versions_use_case),
]


__all__ = [
    "ActivateSegmentVersionUseCaseDep",
    "AddStaticMemberUseCaseDep",
    "ArchiveSegmentDefinitionUseCaseDep",
    "CreateSegmentDefinitionUseCaseDep",
    "CreateSegmentVersionUseCaseDep",
    "GetSegmentDefinitionUseCaseDep",
    "GetSegmentVersionUseCaseDep",
    "ListSegmentDefinitionsUseCaseDep",
    "ListStaticMembersUseCaseDep",
    "ListSegmentVersionsUseCaseDep",
    "RemoveStaticMemberUseCaseDep",
    "SegmentVersionDslConfigValidatorDep",
    "UpdateSegmentDefinitionUseCaseDep",
    "get_activate_segment_version_use_case",
    "get_add_static_member_use_case",
    "get_archive_segment_definition_use_case",
    "get_create_segment_definition_use_case",
    "get_create_segment_version_use_case",
    "get_get_segment_definition_use_case",
    "get_get_segment_version_use_case",
    "get_list_segment_definitions_use_case",
    "get_list_static_members_use_case",
    "get_list_segment_versions_use_case",
    "get_remove_static_member_use_case",
    "get_segment_version_dsl_config_validator",
    "get_update_segment_definition_use_case",
]
