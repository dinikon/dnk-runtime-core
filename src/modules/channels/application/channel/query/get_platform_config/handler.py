from src.modules.channels.application.channel.query.get_platform_config.query import (
    GetPlatformConfigQuery,
)
from src.modules.channels.application.channel.query.get_platform_config.dto import (
    GetPlatformConfigResultDTO,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol


class GetPlatformConfigHandler:
    """Выполняет чтение get_platform_config без write repository и восстановления агрегатов."""

    def __init__(self, registry: PluginRegistryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.registry = registry

    async def execute(
        self, query: GetPlatformConfigQuery
    ) -> GetPlatformConfigResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return GetPlatformConfigResultDTO(self.registry.manifest(query.platform_kind))
