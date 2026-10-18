from dataclasses import dataclass
from src.modules.channels.application.plugin_contract import PluginManifestDTO


@dataclass(frozen=True, slots=True)
class ListPlatformsResultDTO:
    """Возвращает проекцию сценария list_platforms."""

    items: tuple[PluginManifestDTO, ...]
