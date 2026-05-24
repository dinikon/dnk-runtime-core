from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.config.infrastructure.email_config import EmailProvider, EmailSettings
from src.modules.shared.application.email import EmailServicePort
from src.modules.shared.infrastructure.email import (
    ResendEmailTransport,
    SmtpEmailTransport,
    SystemEmailService,
)


def build_email_service(settings: EmailSettings) -> EmailServicePort:
    """Создает email service по активному transport provider."""
    if settings.provider == EmailProvider.RESEND:
        return SystemEmailService(ResendEmailTransport())
    return SystemEmailService(SmtpEmailTransport.from_settings(settings))


default_email_service = build_email_service(dnk_config.EMAIL)


def get_email_service() -> EmailServicePort:
    """Возвращает singleton email service из конфигурации приложения."""
    return default_email_service


EmailServiceDep = Annotated[EmailServicePort, Depends(get_email_service)]

__all__ = [
    "EmailServiceDep",
    "build_email_service",
    "default_email_service",
    "get_email_service",
]
