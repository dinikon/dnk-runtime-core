from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.config.infrastructure.email_config import EmailSettings
from src.modules.identity.application.email.email_service_port import EmailServicePort
from src.modules.identity.infrastructure.email.system_email_service import (
    SystemEmailService,
)
from src.modules.shared.presentation.email.depends import build_email_transport


def build_email_service(settings: EmailSettings) -> EmailServicePort:
    """Создает email service по активному transport provider."""
    return SystemEmailService(build_email_transport(settings))


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
