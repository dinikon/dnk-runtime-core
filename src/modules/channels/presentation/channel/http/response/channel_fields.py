from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.channels.domain.channel.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.types import JsonObject


class ConfigResponse(BaseModel):
    """Публичная конфигурация без credentials."""

    version: int
    endpoint: str
    settings: JsonObject


class IdentityResponse(BaseModel):
    """Подтверждённый устойчивый ключ магазина."""

    namespace: str
    key: str


class VerificationResponse(BaseModel):
    """Текущее состояние проверки."""

    job_id: UUID
    config_revision: int
    status: VerificationStatus
    checked_at: datetime | None
    error_code: str | None


class ChannelResponseFields(BaseModel):
    """Общие поля публичного представления канала для read-контрактов."""

    id: UUID
    name: str
    platform_kind: str
    revision: int
    config: ConfigResponse
    config_revision: int
    identity: IdentityResponse | None
    verification: VerificationResponse
    created_at: datetime
    updated_at: datetime
    recovery_required: bool
    available_capabilities: tuple[str, ...]
