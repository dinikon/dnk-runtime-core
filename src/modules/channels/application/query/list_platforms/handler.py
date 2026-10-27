from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.query.list_platforms.query import (
    ListPlatformsQuery,
)
from src.modules.channels.application.query.list_platforms.dto import ListPlatformsDTO


class ListPlatformsHandler:
    """Читает возможности и схемы платформ из registry."""

    def __init__(self, platforms: PlatformRegistry) -> None:
        """Принимает реестр установленных пакетов."""
        self.platforms = platforms

    async def execute(self, query: ListPlatformsQuery) -> ListPlatformsDTO:
        """Возвращает декларации без обращений к внешнему API."""
        return ListPlatformsDTO(self.platforms.manifests())
