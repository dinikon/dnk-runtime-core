from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.query.list_kinds.dto import ChannelKindListItemDTO


class ListChannelKindItemResponse(BaseModel):
    """Определяет HTTP-ответ сценария list_kinds без credentials."""

    kind: str
    type: str
    label: str
    can_configure: bool
    unavailable_reason: str | None

    @classmethod
    def from_dto(cls, dto: ChannelKindListItemDTO) -> Self:
        """Явно переносит разрешённые поля результата Application в HTTP-ответ."""
        return cls(
            kind=dto.kind,
            type=dto.type,
            label=dto.label,
            can_configure=dto.can_configure,
            unavailable_reason=dto.unavailable_reason,
        )
