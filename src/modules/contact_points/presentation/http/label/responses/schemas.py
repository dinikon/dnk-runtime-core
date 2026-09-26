from uuid import UUID
from typing import Literal
from pydantic import BaseModel


class LabelResponse(BaseModel):
    """Настройка подписи для формы и административной страницы."""

    id: UUID
    type: Literal["phone", "email"]
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto):
        """Преобразует VO в HTTP UUID."""
        return cls(
            id=dto.id.uuid, type=dto.type.value, name=dto.name, is_active=dto.is_active
        )


__all__ = ["LabelResponse"]
