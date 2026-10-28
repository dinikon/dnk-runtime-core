from uuid import UUID
from src.modules.channels.application.catalog_binding.usage import CatalogBindingUsage


class ChannelsCatalogUsage:
    """Переводит публичный контракт Channels в порт владельца Catalog."""

    def __init__(self, usage: CatalogBindingUsage) -> None:
        """Не читает Channels ORM."""
        self.usage = usage

    async def used(self, root_id: UUID, position_id: UUID | None = None) -> bool:
        """Не скрывает использование из-за ограничений интерфейса текущего актора."""
        return await self.usage.used(root_id, position_id)
