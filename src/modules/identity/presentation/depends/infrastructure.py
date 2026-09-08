from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.service import (
    OtpService,
    OtpServiceProtocol,
    SessionService,
    SessionServiceProtocol,
)
from src.modules.identity.application.ports import (
    OtpChallengeStorePort,
    SessionStorePort,
    TenantContextReaderPort,
)
from src.modules.identity.domain.user import UserRepositoryProtocol
from src.modules.identity.infrastructure.adapter import (
    TenancyTenantContextReaderAdapter,
    TokenManagerBackedOtpChallengeStore,
    TokenManagerBackedSessionStore,
)
from src.modules.shared.presentation.email.depends import (
    EmailServiceDep,
    get_email_service,
)
from src.modules.identity.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.shared.presentation.tokens.depends import (
    TokenManagerDep,
    default_token_manager,
    get_token_manager,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.presentation.depends.application import (
    TenantRequestContextByHostUseCaseDep,
)


def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    """Создает SQLAlchemy user repository для текущей UoW."""
    return SqlAlchemyUserRepository(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


UsersRepositoryDep = Annotated[
    UserRepositoryProtocol,
    Depends(get_users_repository),
]


def get_auth_settings() -> IdentityAuthSettings:
    """Возвращает auth settings из конфигурации приложения."""
    return dnk_config.AUTH


AuthSettingsDep = Annotated[IdentityAuthSettings, Depends(get_auth_settings)]


def get_otp_service(settings: AuthSettingsDep) -> OtpServiceProtocol:
    """Создает OTP service с длиной кода из auth settings."""
    return OtpService(settings.otp_code_length)


OtpServiceDep = Annotated[OtpServiceProtocol, Depends(get_otp_service)]


def get_session_service() -> SessionServiceProtocol:
    """Создает session service для генерации session tokens."""
    return SessionService()


SessionServiceDep = Annotated[SessionServiceProtocol, Depends(get_session_service)]


def get_tenant_context_reader(
    use_case: TenantRequestContextByHostUseCaseDep,
) -> TenantContextReaderPort:
    """Создает adapter чтения tenant context из tenancy use case."""
    return TenancyTenantContextReaderAdapter(use_case)


TenantContextReaderDep = Annotated[
    TenantContextReaderPort,
    Depends(get_tenant_context_reader),
]


def get_otp_challenge_store(
    token_manager: TokenManagerDep,
) -> OtpChallengeStorePort:
    """Создает OTP challenge store поверх TokenManager."""
    return TokenManagerBackedOtpChallengeStore(token_manager)


OtpChallengeStoreDep = Annotated[
    OtpChallengeStorePort,
    Depends(get_otp_challenge_store),
]


def get_session_store(token_manager: TokenManagerDep) -> SessionStorePort:
    """Создает session store поверх TokenManager."""
    return TokenManagerBackedSessionStore(token_manager)


SessionStoreDep = Annotated[SessionStorePort, Depends(get_session_store)]


__all__ = [
    "AuthSettingsDep",
    "EmailServiceDep",
    "OtpChallengeStoreDep",
    "OtpServiceDep",
    "SessionServiceDep",
    "SessionStoreDep",
    "TenantContextReaderDep",
    "TokenManagerDep",
    "UsersRepositoryDep",
    "default_token_manager",
    "get_auth_settings",
    "get_email_service",
    "get_otp_challenge_store",
    "get_otp_service",
    "get_session_service",
    "get_session_store",
    "get_tenant_context_reader",
    "get_token_manager",
    "get_users_repository",
]
