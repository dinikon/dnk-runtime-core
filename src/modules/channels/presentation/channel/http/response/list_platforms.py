from pydantic import BaseModel

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
