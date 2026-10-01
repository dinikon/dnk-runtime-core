from __future__ import annotations
from fastapi import Depends
from src.modules.identity.application.user.command.create_tenant_admin.handler import (
    CreateTenantAdminHandler,
)
from src.modules.identity.application.user.command.update_current_user_profile.handler import (
    UpdateCurrentUserProfileHandler,
)
from src.modules.identity.application.user.query.get_current_user.handler import (
    GetCurrentUserHandler,
)
from src.modules.identity.presentation.auth.providers import SessionStoreDep
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from typing import Annotated


def get_create_tenant_admin_handler(
    users_repository: UsersRepositoryDep,
) -> CreateTenantAdminHandler:
    """Создает provisioning user service."""
    return CreateTenantAdminHandler(users_repository)


CreateTenantAdminHandlerDep = Annotated[
    CreateTenantAdminHandler, Depends(get_create_tenant_admin_handler)
]


def get_current_user_handler(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> GetCurrentUserHandler:
    """Создает use case получения текущего пользователя."""
    return GetCurrentUserHandler(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


GetCurrentUserHandlerDep = Annotated[
    GetCurrentUserHandler, Depends(get_current_user_handler)
]


def get_update_current_user_profile_handler(
    uow: UoWDep,
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> UpdateCurrentUserProfileHandler:
    """Создает use case обновления профиля текущего пользователя."""
    return UpdateCurrentUserProfileHandler(
        uow=uow,
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


UpdateCurrentUserProfileHandlerDep = Annotated[
    UpdateCurrentUserProfileHandler, Depends(get_update_current_user_profile_handler)
]
