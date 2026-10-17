from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.storage_provider.query.list_providers.dto import (
    ProviderListItemDTO,
)


class ListProvidersItemResponse(BaseModel):
    """HTTP-проекция сценария list_providers, отделённая от Application DTO."""

    id: UUID
    name: str
    kind: str
    is_system: bool

    @classmethod
    def from_dto(cls, dto: ProviderListItemDTO) -> "ListProvidersItemResponse":
        """Явно преобразует специализированный результат сценария."""
        return cls(id=dto.id, name=dto.name, kind=dto.kind, is_system=dto.is_system)
