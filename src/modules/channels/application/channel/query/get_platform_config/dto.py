from dataclasses import dataclass
from src.modules.channels.application.plugin_contract import PluginManifestDTO


@dataclass(frozen=True, slots=True)
class GetPlatformConfigResultDTO:
    """Возвращает проекцию сценария get_platform_config."""

    manifest: PluginManifestDTO
