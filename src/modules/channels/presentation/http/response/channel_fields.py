from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.application.port.query_repository import (
    ConnectionConfigReadRow,
    ResourceIdentityReadRow,
    VerificationReadRow,
)


class ConfigResponse(BaseModel):
    """Публичная конфигурация без credentials."""

    version: int
    endpoint: str
    settings: JsonObject

    @classmethod
    def from_projection(cls, value: ConnectionConfigReadRow) -> "ConfigResponse":
        """Явно преобразует публичное значение Application в HTTP-схему."""
        return cls(
            version=value.version,
            endpoint=value.endpoint,
            settings=value.settings,
        )


class IdentityResponse(BaseModel):
    """Подтверждённый устойчивый ключ магазина."""

    namespace: str
    key: str

    @classmethod
    def from_projection(cls, value: ResourceIdentityReadRow) -> "IdentityResponse":
        """Явно преобразует публичное значение Application в HTTP-схему."""
        return cls(
            namespace=value.namespace,
            key=value.key,
        )


class VerificationResponse(BaseModel):
    """Текущее состояние проверки."""

    job_id: UUID
    config_revision: int
    status: VerificationStatus
    checked_at: datetime | None
    error_code: str | None

    @classmethod
    def from_projection(cls, value: VerificationReadRow) -> "VerificationResponse":
        """Явно преобразует публичное значение Application в HTTP-схему."""
        return cls(
            job_id=value.job_id,
            config_revision=value.config_revision,
            status=value.status,
            checked_at=value.checked_at,
            error_code=value.error_code,
        )
