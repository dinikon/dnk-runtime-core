from fastapi import Depends
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.auth.service.session_issuer import SessionIssuer
from src.modules.identity.presentation.access.providers import AccessRepositoryDep
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.identity.presentation.auth.providers import SessionServiceDep
from src.modules.identity.presentation.auth.providers import SessionStoreDep
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from typing import Annotated


def get_session_authentication(
    access: AccessRepositoryDep,
    sessions: SessionStoreDep,
    tenant_reader: TenantContextReaderDep,
    users: UsersRepositoryDep,
) -> SessionAuthenticationService:
    return SessionAuthenticationService(
        access=access, sessions=sessions, tenant_reader=tenant_reader, users=users
    )


SessionAuthenticationServiceDep = Annotated[
    SessionAuthenticationService, Depends(get_session_authentication)
]


def get_session_issuer(
    session_service: SessionServiceDep,
    sessions: SessionStoreDep,
    settings: AuthSettingsDep,
) -> SessionIssuer:
    return SessionIssuer(
        session_service=session_service, sessions=sessions, settings=settings
    )


SessionIssuerDep = Annotated[SessionIssuer, Depends(get_session_issuer)]
