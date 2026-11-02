from pydantic import BaseModel
from src.modules.channels.application.query.list_platforms.dto import ListPlatformsDTO

from src.modules.channels.domain.types import JsonObject


class PlatformResponse(BaseModel):
    """Схемы и декларация одного установленного платформенного пакета."""

    kind: str
    title: str
    config_version: int
    config_schema: JsonObject
    credentials_schema: JsonObject
    supported_capabilities: tuple[str, ...]


class ListPlatformsResponse(BaseModel):
    """Каталог платформ для Console."""

    items: tuple[PlatformResponse, ...]

    @classmethod
    def from_dto(cls, value: ListPlatformsDTO) -> "ListPlatformsResponse":
        """Выдаёт только публичные поля manifest установленных платформ."""
        return cls(
            items=tuple(
                PlatformResponse(
                    kind=item.kind,
                    title=item.title,
                    config_version=item.config_version,
                    config_schema=item.config_schema,
                    credentials_schema=item.credentials_schema,
                    supported_capabilities=item.supported_capabilities,
                )
                for item in value.items
            )
        )
