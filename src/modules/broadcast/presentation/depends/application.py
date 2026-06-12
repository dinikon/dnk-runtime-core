from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.broadcast.application.broadcast.use_case import (
    CreateBroadcastUseCase,
    DescribeBroadcastFieldsUseCase,
    GetBroadcastUseCase,
    ListBroadcastsUseCase,
)
from src.modules.broadcast.presentation.depends.infrastructure import (
    BroadcastCommandRepositoryDep,
    BroadcastFieldsDescriptionRepositoryDep,
    BroadcastQueryRepositoryDep,
)
from src.modules.shared.presentation import ClockDep, UuidDep


def get_create_broadcast_use_case(
    command_repository: BroadcastCommandRepositoryDep,
    clock: ClockDep,
    uuid_generator: UuidDep,
) -> CreateBroadcastUseCase:
    """Создает use case создания broadcast."""
    return CreateBroadcastUseCase(
        command_repository=command_repository,
        clock=clock,
        uuid_generator=uuid_generator,
    )


def get_list_broadcasts_use_case(
    query_repository: BroadcastQueryRepositoryDep,
) -> ListBroadcastsUseCase:
    """Создает use case списка broadcast."""
    return ListBroadcastsUseCase(query_repository=query_repository)


def get_get_broadcast_use_case(
    query_repository: BroadcastQueryRepositoryDep,
) -> GetBroadcastUseCase:
    """Создает use case чтения broadcast."""
    return GetBroadcastUseCase(query_repository=query_repository)


def get_describe_broadcast_fields_use_case(
    repository: BroadcastFieldsDescriptionRepositoryDep,
) -> DescribeBroadcastFieldsUseCase:
    """Создает use case чтения описания broadcast-модели."""
    return DescribeBroadcastFieldsUseCase(repository)


CreateBroadcastUseCaseDep = Annotated[
    CreateBroadcastUseCase,
    Depends(get_create_broadcast_use_case),
]

DescribeBroadcastFieldsUseCaseDep = Annotated[
    DescribeBroadcastFieldsUseCase,
    Depends(get_describe_broadcast_fields_use_case),
]

ListBroadcastsUseCaseDep = Annotated[
    ListBroadcastsUseCase,
    Depends(get_list_broadcasts_use_case),
]

GetBroadcastUseCaseDep = Annotated[
    GetBroadcastUseCase,
    Depends(get_get_broadcast_use_case),
]


__all__ = [
    "CreateBroadcastUseCaseDep",
    "DescribeBroadcastFieldsUseCaseDep",
    "GetBroadcastUseCaseDep",
    "ListBroadcastsUseCaseDep",
    "get_create_broadcast_use_case",
    "get_describe_broadcast_fields_use_case",
    "get_get_broadcast_use_case",
    "get_list_broadcasts_use_case",
]
