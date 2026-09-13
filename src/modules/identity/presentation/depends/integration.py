"""Composition of identity integration adapters on the request UoW."""

from typing import Annotated
from fastapi import Depends, Request

from src.config import dnk_config
from src.modules.identity.application.access_service import IdentityAccessService
from src.modules.identity.application.cloud_auth_service import CloudAuthService
from src.modules.identity.infrastructure.adapter.oidc_client import OidcClient
from src.modules.identity.infrastructure.repository.access_repository import (
    AccessRepository,
)
from src.modules.identity.presentation.depends.infrastructure import (
    UsersRepositoryDep,
    SessionStoreDep,
    TenantContextReaderDep,
    TokenManagerDep,
    OtpServiceDep,
    SessionServiceDep,
    EmailServiceDep,
    AuthSettingsDep,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_access_service(
    uow: UoWDep,
    users: UsersRepositoryDep,
    sessions: SessionStoreDep,
    tenant_reader: TenantContextReaderDep,
    tokens: TokenManagerDep,
    otp: OtpServiceDep,
    session_service: SessionServiceDep,
    email: EmailServiceDep,
    settings: AuthSettingsDep,
):
    from src.modules.control_plane.infrastructure.services import AccessProjectionWriter

    return IdentityAccessService(
        uow=uow,
        users=users,
        access=AccessRepository(
            uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        ),
        sessions=sessions,
        tenant_reader=tenant_reader,
        tokens=tokens,
        otp=otp,
        session_service=session_service,
        email=email,
        settings=settings,
        projections=AccessProjectionWriter(uow.session),
    )


AccessServiceDep = Annotated[IdentityAccessService, Depends(get_access_service)]
_oidc_clients = {}


def get_cloud_service(request: Request, uow: UoWDep, local: AccessServiceDep):
    from src.modules.control_plane.infrastructure.services import CloudConnectionReader

    origin = dnk_config.CONTROL_PLANE.public_origin
    oidc = getattr(request.app.state, "oidc_client", None) or _oidc_clients.get(origin)
    if oidc is None:
        oidc = _oidc_clients[origin] = OidcClient(origin)
    return CloudAuthService(local, CloudConnectionReader(uow.session), oidc)


CloudServiceDep = Annotated[CloudAuthService, Depends(get_cloud_service)]
