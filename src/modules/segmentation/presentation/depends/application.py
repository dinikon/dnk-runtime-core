from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.segmentation.application.segment_static_member import (
    AddStaticMemberUseCase,
    ListStaticMembersUseCase,
    RemoveStaticMemberUseCase,
)
from src.modules.segmentation.presentation.depends.infrastructure import (
    ContactLookupDep,
    SegmentDefinitionRuntimeRepositoryDep,
    SegmentStaticMemberCommandRepositoryDep,
    SegmentStaticMemberQueryRepositoryDep,
)
from src.modules.shared.presentation import UuidDep


def get_add_static_member_use_case(
    segment_repository: SegmentDefinitionRuntimeRepositoryDep,
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
    segment_repository: SegmentDefinitionRuntimeRepositoryDep,
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


__all__ = [
    "AddStaticMemberUseCaseDep",
    "ListStaticMembersUseCaseDep",
    "RemoveStaticMemberUseCaseDep",
    "get_add_static_member_use_case",
    "get_list_static_members_use_case",
    "get_remove_static_member_use_case",
]
