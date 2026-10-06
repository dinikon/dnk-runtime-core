from datetime import datetime
from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.command.update_channel.dto import (
    UpdateChannelResultDTO,
)


class UpdateChannelResponse(BaseModel):
    """Определяет HTTP-ответ сценария update_channel без credentials."""

    id: UUID
    name: str
    kind: str
    type: str
    config_version: int
    connection_settings: dict[str, str]
    configured_secret_fields: list[str]
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: UpdateChannelResultDTO) -> Self:
        """Явно переносит разрешённые поля результата Application в HTTP-ответ."""
        return cls(
            id=dto.id,
            name=dto.name,
            kind=dto.kind,
            type=dto.type,
            config_version=dto.config_version,
            connection_settings=dto.connection_settings,
            configured_secret_fields=list(dto.configured_secret_fields),
            is_active=dto.is_active,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
