from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.application.provisioning.services.user_service import (
    UserService,
    UserServiceProtocol,
)
from src.modules.identity.presentation.depends.repositories import UsersRepositoryDep


def get_user_service(users_repository: UsersRepositoryDep) -> UserServiceProtocol:
    return UserService(users_repository)


UserServiceDep = Annotated[UserServiceProtocol, Depends(get_user_service)]

__all__ = ["get_user_service", "UserServiceDep"]
