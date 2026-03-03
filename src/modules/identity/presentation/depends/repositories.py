from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.application.provisioning.ports.repositories import (
    UserRepositoryProtocol,
)
from src.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.modules.shared.depends.uow import UoWDep


def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    return SqlAlchemyUserRepository(uow.session)


UsersRepositoryDep = Annotated[
    UserRepositoryProtocol,
    Depends(get_users_repository),
]

__all__ = ["get_users_repository", "UsersRepositoryDep"]
