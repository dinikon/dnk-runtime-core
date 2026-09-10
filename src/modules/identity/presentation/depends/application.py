from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.identity.application.auth import (
    AuthenticateBySessionUseCase,
    AuthenticateBySessionUseCaseProtocol,
    ConfirmEmailOtpUseCase,
    GetCurrentUserUseCase,
    LogoutCurrentSessionUseCase,
    RequestEmailOtpUseCase,
    UpdateCurrentUserProfileUseCase,
)
from src.modules.identity.application.user import UserService, UserServiceProtocol
from src.modules.identity.presentation.depends.infrastructure import (
    AuthSettingsDep,
    EmailServiceDep,
    OtpChallengeStoreDep,
    OtpServiceDep,
    SessionServiceDep,
    SessionStoreDep,
    TenantContextReaderDep,
    UsersRepositoryDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_user_service(users_repository: UsersRepositoryDep) -> UserServiceProtocol:
    """Создает provisioning user service."""
    return UserService(users_repository)


UserServiceDep = Annotated[UserServiceProtocol, Depends(get_user_service)]


def get_request_email_otp_use_case(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    otp_service: OtpServiceDep,
    email_service: EmailServiceDep,
    settings: AuthSettingsDep,
) -> RequestEmailOtpUseCase:
    """Создает use case запроса email OTP."""
    return RequestEmailOtpUseCase(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        otp_challenge_store=otp_challenge_store,
        otp_service=otp_service,
        email_service=email_service,
        otp_ttl_seconds=settings.otp_token_ttl_seconds,
    )


RequestEmailOtpUseCaseDep = Annotated[
    RequestEmailOtpUseCase,
    Depends(get_request_email_otp_use_case),
]


def get_authenticate_by_session_use_case(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> AuthenticateBySessionUseCaseProtocol:
    """Создает use case аутентификации по session."""
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
    users_repository: UsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    session_store: SessionStoreDep,
    otp_service: OtpServiceDep,
    session_service: SessionServiceDep,
    settings: AuthSettingsDep,
) -> ConfirmEmailOtpUseCase:
    """Создает use case подтверждения email OTP."""
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
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> GetCurrentUserUseCase:
    """Создает use case получения текущего пользователя."""
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
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> UpdateCurrentUserProfileUseCase:
    """Создает use case обновления профиля текущего пользователя."""
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
    """Создает use case logout текущей session."""
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
    "UserServiceDep",
    "get_authenticate_by_session_use_case",
    "get_confirm_email_otp_use_case",
    "get_current_user_use_case",
    "get_logout_current_session_use_case",
    "get_request_email_otp_use_case",
    "get_update_current_user_profile_use_case",
    "get_user_service",
]
