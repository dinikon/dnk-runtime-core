from src.modules.channels.application.channel.query.list_kinds.dto import (
    ChannelKindListItemDTO,
)
from src.modules.channels.application.channel.port.registry import ChannelRegistryPort
from src.modules.channels.application.channel.query.list_kinds.query import (
    ListKindsQuery,
)


class ListKindsHandler:
    """Координирует выдачу доступности платформ из реестра."""

    def __init__(self, registry: ChannelRegistryPort) -> None:
        """Принимает порт сценария из внешней сборки зависимостей."""
        self._registry = registry

    async def execute(
        self, query: ListKindsQuery
    ) -> tuple[ChannelKindListItemDTO, ...]:
        """Преобразует определения реестра в результат конкретного сценария."""
        return tuple(
            ChannelKindListItemDTO(
                kind=definition.kind.value,
                type=definition.type.value,
                label=definition.label,
                can_configure=definition.can_configure,
                unavailable_reason=definition.unavailable_reason,
            )
            for definition in self._registry.list_all()
        )
