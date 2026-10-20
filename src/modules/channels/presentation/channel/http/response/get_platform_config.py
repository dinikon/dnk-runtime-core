from pydantic import BaseModel
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class GetPlatformConfigManifestResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария get_platform_config."""

    kind: str
    label: str
    sdk_version: int
    config_version: int
    capabilities: tuple[str, ...]
    credentials_schema: dict[str, JsonValue]
    endpoint_schema: dict[str, JsonValue]
    settings_schema: dict[str, JsonValue]


class GetPlatformConfigResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария get_platform_config."""

    manifest: GetPlatformConfigManifestResponse
