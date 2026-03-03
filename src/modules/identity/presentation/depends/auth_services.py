from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from src.config import dnk_config
from src.config.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.ports.email_sender import EmailSenderPort
from src.modules.identity.application.auth.services.otp_service import (
    OtpService,
    OtpServiceProtocol,
)
from src.modules.identity.application.auth.services.session_service import (
    SessionService,
    SessionServiceProtocol,
)
from src.modules.shared.tokens import (
    InMemoryTokenBackend,
    RedisTokenBackend,
    TokenManager,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SentLoginCode:
    email: str
    code: str


class InMemoryEmailSender(EmailSenderPort):
    def __init__(self) -> None:
        self.sent_codes: list[SentLoginCode] = []

    async def send_login_code(self, email: str, code: str) -> None:
        self.sent_codes.append(SentLoginCode(email=email, code=code))


default_email_sender = InMemoryEmailSender()


def get_auth_settings() -> IdentityAuthSettings:
    return dnk_config.AUTH


AuthSettingsDep = Annotated[IdentityAuthSettings, Depends(get_auth_settings)]


def get_token_manager(request: Request) -> TokenManager:
    return getattr(request.app.state, "token_manager", default_token_manager)


TokenManagerDep = Annotated[TokenManager, Depends(get_token_manager)]


def get_email_sender(request: Request) -> EmailSenderPort:
    return getattr(request.app.state, "email_sender", default_email_sender)


EmailSenderDep = Annotated[EmailSenderPort, Depends(get_email_sender)]


def get_otp_service(settings: AuthSettingsDep) -> OtpServiceProtocol:
    return OtpService(settings.otp_code_length)


OtpServiceDep = Annotated[OtpServiceProtocol, Depends(get_otp_service)]


def get_session_service() -> SessionServiceProtocol:
    return SessionService()


def _build_default_token_manager() -> TokenManager:
    try:
        return TokenManager(RedisTokenBackend.from_config())
    except RuntimeError as exc:
        log.warning(
            "Redis token backend is unavailable, using in-memory fallback: %s",
            exc,
        )
        return TokenManager(InMemoryTokenBackend())


default_token_manager = _build_default_token_manager()


SessionServiceDep = Annotated[SessionServiceProtocol, Depends(get_session_service)]


__all__ = [
    "AuthSettingsDep",
    "EmailSenderDep",
    "InMemoryEmailSender",
    "OtpServiceDep",
    "SentLoginCode",
    "SessionServiceDep",
    "TokenManagerDep",
    "default_email_sender",
    "default_token_manager",
    "get_auth_settings",
    "get_email_sender",
    "get_otp_service",
    "get_session_service",
    "get_token_manager",
]
