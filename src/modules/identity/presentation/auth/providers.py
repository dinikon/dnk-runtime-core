from __future__ import annotations
from fastapi import Depends
from src.config import dnk_config
from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.port.otp_challenge_store import (
    OtpChallengeStorePort,
)
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.service.otp_service import OtpService
from src.modules.identity.application.auth.service.otp_service import OtpServiceProtocol
from src.modules.identity.application.auth.service.session_service import SessionService
from src.modules.identity.application.auth.service.session_service import (
    SessionServiceProtocol,
)
from src.modules.identity.infrastructure.auth.otp_challenge_store import (
    TokenManagerBackedOtpChallengeStore,
)
from src.modules.identity.infrastructure.auth.session_store import (
    TokenManagerBackedSessionStore,
)
from src.modules.identity.infrastructure.auth.tenant_context_reader import (
    TenancyTenantContextReaderAdapter,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.tenancy.presentation.depends.application import (
    TenantRequestContextByHostUseCaseDep,
)
from typing import Annotated


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
    TenantContextReaderPort, Depends(get_tenant_context_reader)
]


def get_otp_challenge_store(token_manager: TokenManagerDep) -> OtpChallengeStorePort:
    """Создает OTP challenge store поверх TokenManager."""
    return TokenManagerBackedOtpChallengeStore(token_manager)


OtpChallengeStoreDep = Annotated[
    OtpChallengeStorePort, Depends(get_otp_challenge_store)
]


def get_session_store(token_manager: TokenManagerDep) -> SessionStorePort:
    """Создает session store поверх TokenManager."""
    return TokenManagerBackedSessionStore(token_manager)


SessionStoreDep = Annotated[SessionStorePort, Depends(get_session_store)]
