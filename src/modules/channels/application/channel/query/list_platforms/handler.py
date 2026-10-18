from src.modules.channels.application.channel.query.list_platforms.query import (
    ListPlatformsQuery,
)
from src.modules.channels.application.channel.query.list_platforms.dto import (
    ListPlatformsResultDTO,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol


class ListPlatformsHandler:
    """Выполняет чтение list_platforms без write repository и восстановления агрегатов."""

    def __init__(self, registry: PluginRegistryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.registry = registry

    async def execute(self, query: ListPlatformsQuery) -> ListPlatformsResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return ListPlatformsResultDTO(self.registry.manifests())
