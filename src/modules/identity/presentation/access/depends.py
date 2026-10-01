from __future__ import annotations
from fastapi import Depends, Request
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.application.access.command.change_user_access.handler import (
    ChangeUserAccessHandler,
)
from src.modules.identity.application.access.query.list_users.handler import (
    ListUsersHandler,
)
from src.modules.identity.infrastructure.access.allow_all_authorization_service import (
    AllowAllAuthorizationService,
)
from src.modules.identity.presentation.access.providers import AccessProjectionsDep
from src.modules.identity.presentation.access.providers import AccessRepositoryDep
from src.modules.identity.presentation.auth.service_depends import (
    SessionAuthenticationServiceDep,
)
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from typing import Annotated

default_authorization_service: AuthorizationServiceProtocol = (
    AllowAllAuthorizationService()
)


def get_authorization_service(request: Request) -> AuthorizationServiceProtocol:
    """Возвращает authorization service из app.state или default allow-all."""
    from_state = getattr(request.app.state, "authorization_service", None)
    if from_state is not None:
        return from_state
    return default_authorization_service


AuthorizationServiceDep = Annotated[
    AuthorizationServiceProtocol, Depends(get_authorization_service)
]


def get_list_users_handler(
    access: AccessRepositoryDep, authentication: SessionAuthenticationServiceDep
) -> ListUsersHandler:
    return ListUsersHandler(access=access, authentication=authentication)


ListUsersHandlerDep = Annotated[ListUsersHandler, Depends(get_list_users_handler)]


def get_change_user_access_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    projections: AccessProjectionsDep,
    uow: UoWDep,
    users: UsersRepositoryDep,
) -> ChangeUserAccessHandler:
    return ChangeUserAccessHandler(
        access=access,
        authentication=authentication,
        projections=projections,
        uow=uow,
        users=users,
    )


ChangeUserAccessHandlerDep = Annotated[
    ChangeUserAccessHandler, Depends(get_change_user_access_handler)
]
