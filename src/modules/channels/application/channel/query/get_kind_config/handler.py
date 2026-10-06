from src.modules.channels.application.channel.query.get_kind_config.dto import (
    ChannelKindConfigDTO,
)
from src.modules.channels.application.channel.port.registry import ChannelRegistryPort
from src.modules.channels.application.channel.query.get_kind_config.query import (
    GetKindConfigQuery,
)


class GetKindConfigHandler:
    """Координирует выдачу версии и схемы формы выбранной платформы."""

    def __init__(self, registry: ChannelRegistryPort) -> None:
        """Принимает порт сценария из внешней сборки зависимостей."""
        self._registry = registry

    async def execute(self, query: GetKindConfigQuery) -> ChannelKindConfigDTO:
        """Преобразует определения реестра в результат конкретного сценария."""
        definition = self._registry.get(query.kind)
        return ChannelKindConfigDTO(
            kind=definition.kind.value,
            type=definition.type.value,
            label=definition.label,
            can_configure=definition.can_configure,
            unavailable_reason=definition.unavailable_reason,
            config_version=definition.config_version,
            config=definition.config,
        )
