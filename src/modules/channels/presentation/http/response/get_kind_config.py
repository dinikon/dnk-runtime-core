from typing import Any
from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.query.get_kind_config.dto import (
    ChannelKindConfigDTO,
)


class GetKindConfigResponse(BaseModel):
    """Определяет HTTP-ответ сценария get_kind_config без credentials."""

    kind: str
    type: str
    label: str
    can_configure: bool
    unavailable_reason: str | None
    config_version: int
    config: dict[str, Any]

    @classmethod
    def from_dto(cls, dto: ChannelKindConfigDTO) -> Self:
        """Явно переносит разрешённые поля результата Application в HTTP-ответ."""
        return cls(
            kind=dto.kind,
            type=dto.type,
            label=dto.label,
            can_configure=dto.can_configure,
            unavailable_reason=dto.unavailable_reason,
            config_version=dto.config_version,
            config=dto.config,
        )
