from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.application.auth.use_cases.authenticate_by_session import (
    AuthenticateBySessionUseCase,
    AuthenticateBySessionUseCaseProtocol,
)
from src.modules.identity.application.auth.use_cases.confirm_email_otp import (
    ConfirmEmailOtpUseCase,
)
from src.modules.identity.application.auth.use_cases.get_current_user import (
    GetCurrentUserUseCase,
)
from src.modules.identity.application.auth.use_cases.logout_current_session import (
    LogoutCurrentSessionUseCase,
)
from src.modules.identity.application.auth.use_cases.request_email_otp import (
    RequestEmailOtpUseCase,
)
from src.modules.identity.application.auth.use_cases.update_current_user_profile import (
    UpdateCurrentUserProfileUseCase,
)
from src.modules.identity.presentation.depends.auth_repositories import (
    AuthUsersRepositoryDep,
    OtpChallengeStoreDep,
    SessionStoreDep,
    TenantContextReaderDep,
)
from src.modules.identity.presentation.depends.auth_services import (
    AuthSettingsDep,
    EmailSenderDep,
    OtpServiceDep,
    SessionServiceDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_request_email_otp_use_case(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: AuthUsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    otp_service: OtpServiceDep,
    email_sender: EmailSenderDep,
    settings: AuthSettingsDep,
) -> RequestEmailOtpUseCase:
    return RequestEmailOtpUseCase(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        otp_challenge_store=otp_challenge_store,
        otp_service=otp_service,
        email_sender=email_sender,
        otp_ttl_seconds=settings.otp_token_ttl_seconds,
    )


RequestEmailOtpUseCaseDep = Annotated[
    RequestEmailOtpUseCase,
    Depends(get_request_email_otp_use_case),
]


def get_authenticate_by_session_use_case(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: AuthUsersRepositoryDep,
    session_store: SessionStoreDep,
) -> AuthenticateBySessionUseCaseProtocol:
    return AuthenticateBySessionUseCase(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


AuthenticateBySessionUseCaseDep = Annotated[
    AuthenticateBySessionUseCaseProtocol,
    Depends(get_authenticate_by_session_use_case),
]


def get_confirm_email_otp_use_case(
    uow: UoWDep,
    tenant_context_reader: TenantContextReaderDep,
    users_repository: AuthUsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    session_store: SessionStoreDep,
    otp_service: OtpServiceDep,
    session_service: SessionServiceDep,
    settings: AuthSettingsDep,
) -> ConfirmEmailOtpUseCase:
    return ConfirmEmailOtpUseCase(
        uow=uow,
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        otp_challenge_store=otp_challenge_store,
        session_store=session_store,
        otp_service=otp_service,
        session_service=session_service,
        session_ttl_seconds=settings.session_ttl_seconds,
    )


ConfirmEmailOtpUseCaseDep = Annotated[
    ConfirmEmailOtpUseCase,
    Depends(get_confirm_email_otp_use_case),
]


def get_current_user_use_case(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: AuthUsersRepositoryDep,
    session_store: SessionStoreDep,
) -> GetCurrentUserUseCase:
    return GetCurrentUserUseCase(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


GetCurrentUserUseCaseDep = Annotated[
    GetCurrentUserUseCase,
    Depends(get_current_user_use_case),
]


def get_update_current_user_profile_use_case(
    uow: UoWDep,
    tenant_context_reader: TenantContextReaderDep,
    users_repository: AuthUsersRepositoryDep,
    session_store: SessionStoreDep,
) -> UpdateCurrentUserProfileUseCase:
    return UpdateCurrentUserProfileUseCase(
        uow=uow,
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


UpdateCurrentUserProfileUseCaseDep = Annotated[
    UpdateCurrentUserProfileUseCase,
    Depends(get_update_current_user_profile_use_case),
]


def get_logout_current_session_use_case(
    tenant_context_reader: TenantContextReaderDep,
    session_store: SessionStoreDep,
) -> LogoutCurrentSessionUseCase:
    return LogoutCurrentSessionUseCase(
        tenant_context_reader=tenant_context_reader,
        session_store=session_store,
    )


LogoutCurrentSessionUseCaseDep = Annotated[
    LogoutCurrentSessionUseCase,
    Depends(get_logout_current_session_use_case),
]


__all__ = [
    "AuthenticateBySessionUseCaseDep",
    "ConfirmEmailOtpUseCaseDep",
    "GetCurrentUserUseCaseDep",
    "LogoutCurrentSessionUseCaseDep",
    "RequestEmailOtpUseCaseDep",
    "UpdateCurrentUserProfileUseCaseDep",
    "get_authenticate_by_session_use_case",
    "get_confirm_email_otp_use_case",
    "get_current_user_use_case",
    "get_logout_current_session_use_case",
    "get_request_email_otp_use_case",
    "get_update_current_user_profile_use_case",
]
