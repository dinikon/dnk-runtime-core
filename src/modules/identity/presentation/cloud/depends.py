from fastapi import Depends
from src.modules.identity.application.cloud.command.complete_cloud_auth.handler import (
    CompleteCloudAuthHandler,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.handler import (
    StartCloudAuthHandler,
)
from src.modules.identity.application.cloud.command.unlink_cloud_identity.handler import (
    UnlinkCloudIdentityHandler,
)
from src.modules.identity.application.cloud.query.get_cloud_status.handler import (
    GetCloudStatusHandler,
)
from src.modules.identity.presentation.access.providers import AccessProjectionsDep
from src.modules.identity.presentation.access.providers import AccessRepositoryDep
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.identity.presentation.auth.service_depends import (
    SessionAuthenticationServiceDep,
)
from src.modules.identity.presentation.auth.service_depends import SessionIssuerDep
from src.modules.identity.presentation.cloud.providers import CloudConnectionsDep
from src.modules.identity.presentation.cloud.providers import OidcClientDep
from src.modules.identity.presentation.cloud.service_depends import (
    CloudConnectionServiceDep,
)
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from typing import Annotated


def get_cloud_status_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    connections: CloudConnectionsDep,
    tenant_reader: TenantContextReaderDep,
) -> GetCloudStatusHandler:
    return GetCloudStatusHandler(
        access=access,
        authentication=authentication,
        connections=connections,
        tenant_reader=tenant_reader,
    )


GetCloudStatusHandlerDep = Annotated[
    GetCloudStatusHandler, Depends(get_cloud_status_handler)
]


def get_start_cloud_auth_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    cloud_connection: CloudConnectionServiceDep,
    oidc: OidcClientDep,
    tenant_reader: TenantContextReaderDep,
    tokens: TokenManagerDep,
) -> StartCloudAuthHandler:
    return StartCloudAuthHandler(
        access=access,
        authentication=authentication,
        cloud_connection=cloud_connection,
        oidc=oidc,
        tenant_reader=tenant_reader,
        tokens=tokens,
    )


StartCloudAuthHandlerDep = Annotated[
    StartCloudAuthHandler, Depends(get_start_cloud_auth_handler)
]


def get_complete_cloud_auth_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    cloud_connection: CloudConnectionServiceDep,
    issuer: SessionIssuerDep,
    oidc: OidcClientDep,
    projections: AccessProjectionsDep,
    tenant_reader: TenantContextReaderDep,
    tokens: TokenManagerDep,
    uow: UoWDep,
    users: UsersRepositoryDep,
) -> CompleteCloudAuthHandler:
    return CompleteCloudAuthHandler(
        access=access,
        authentication=authentication,
        cloud_connection=cloud_connection,
        issuer=issuer,
        oidc=oidc,
        projections=projections,
        tenant_reader=tenant_reader,
        tokens=tokens,
        uow=uow,
        users=users,
    )


CompleteCloudAuthHandlerDep = Annotated[
    CompleteCloudAuthHandler, Depends(get_complete_cloud_auth_handler)
]


def get_unlink_cloud_identity_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    projections: AccessProjectionsDep,
    uow: UoWDep,
) -> UnlinkCloudIdentityHandler:
    return UnlinkCloudIdentityHandler(
        access=access, authentication=authentication, projections=projections, uow=uow
    )


UnlinkCloudIdentityHandlerDep = Annotated[
    UnlinkCloudIdentityHandler, Depends(get_unlink_cloud_identity_handler)
]
