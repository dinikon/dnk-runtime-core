from dataclasses import dataclass
from src.modules.channels.application.port.platform import PlatformManifest


@dataclass(frozen=True, slots=True)
class ListPlatformsDTO:
    """Декларации установленных платформ."""

    items: tuple[PlatformManifest, ...]
