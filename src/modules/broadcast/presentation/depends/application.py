from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.broadcast.application.broadcast.use_case import CreateBroadcastUseCase
from src.modules.broadcast.presentation.depends.infrastructure import (
    BroadcastCommandRepositoryDep,
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


CreateBroadcastUseCaseDep = Annotated[
    CreateBroadcastUseCase,
    Depends(get_create_broadcast_use_case),
]


__all__ = [
    "CreateBroadcastUseCaseDep",
    "get_create_broadcast_use_case",
]
