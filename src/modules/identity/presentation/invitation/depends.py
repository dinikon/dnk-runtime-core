from fastapi import Depends
from src.modules.identity.application.invitation.command.accept_invitation.handler import (
    AcceptInvitationHandler,
)
from src.modules.identity.application.invitation.command.create_invitation.handler import (
    CreateInvitationHandler,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.handler import (
    RequestInvitationOtpHandler,
)
from src.modules.identity.application.invitation.command.revoke_invitation.handler import (
    RevokeInvitationHandler,
)
from src.modules.identity.application.invitation.query.list_invitations.handler import (
    ListInvitationsHandler,
)
from src.modules.identity.presentation.access.providers import AccessRepositoryDep
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.identity.presentation.auth.providers import OtpServiceDep
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.identity.presentation.auth.service_depends import (
    SessionAuthenticationServiceDep,
)
from src.modules.identity.presentation.auth.service_depends import SessionIssuerDep
from src.modules.identity.presentation.email.depends import EmailServiceDep
from src.modules.identity.presentation.invitation.service_depends import (
    InvitationValidatorDep,
)
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from typing import Annotated


def get_list_invitations_handler(
    access: AccessRepositoryDep, authentication: SessionAuthenticationServiceDep
) -> ListInvitationsHandler:
    return ListInvitationsHandler(access=access, authentication=authentication)


ListInvitationsHandlerDep = Annotated[
    ListInvitationsHandler, Depends(get_list_invitations_handler)
]


def get_create_invitation_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    email: EmailServiceDep,
    settings: AuthSettingsDep,
    uow: UoWDep,
    users: UsersRepositoryDep,
) -> CreateInvitationHandler:
    return CreateInvitationHandler(
        access=access,
        authentication=authentication,
        email=email,
        settings=settings,
        uow=uow,
        users=users,
    )


CreateInvitationHandlerDep = Annotated[
    CreateInvitationHandler, Depends(get_create_invitation_handler)
]


def get_revoke_invitation_handler(
    access: AccessRepositoryDep,
    authentication: SessionAuthenticationServiceDep,
    uow: UoWDep,
) -> RevokeInvitationHandler:
    return RevokeInvitationHandler(
        access=access, authentication=authentication, uow=uow
    )


RevokeInvitationHandlerDep = Annotated[
    RevokeInvitationHandler, Depends(get_revoke_invitation_handler)
]


def get_request_invitation_otp_handler(
    email: EmailServiceDep,
    invitations: InvitationValidatorDep,
    otp: OtpServiceDep,
    settings: AuthSettingsDep,
    tenant_reader: TenantContextReaderDep,
    tokens: TokenManagerDep,
) -> RequestInvitationOtpHandler:
    return RequestInvitationOtpHandler(
        email=email,
        invitations=invitations,
        otp=otp,
        settings=settings,
        tenant_reader=tenant_reader,
        tokens=tokens,
    )


RequestInvitationOtpHandlerDep = Annotated[
    RequestInvitationOtpHandler, Depends(get_request_invitation_otp_handler)
]


def get_accept_invitation_handler(
    access: AccessRepositoryDep,
    invitations: InvitationValidatorDep,
    issuer: SessionIssuerDep,
    otp: OtpServiceDep,
    tenant_reader: TenantContextReaderDep,
    tokens: TokenManagerDep,
    uow: UoWDep,
    users: UsersRepositoryDep,
) -> AcceptInvitationHandler:
    return AcceptInvitationHandler(
        access=access,
        invitations=invitations,
        issuer=issuer,
        otp=otp,
        tenant_reader=tenant_reader,
        tokens=tokens,
        uow=uow,
        users=users,
    )


AcceptInvitationHandlerDep = Annotated[
    AcceptInvitationHandler, Depends(get_accept_invitation_handler)
]
