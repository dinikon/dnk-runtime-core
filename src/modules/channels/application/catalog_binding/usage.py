from uuid import UUID
from src.modules.channels.application.catalog_binding.ports import BindingReadPort


class CatalogBindingUsage:
    """Публичный Application контракт использования Catalog, независимо от прав UI."""

    def __init__(self, read: BindingReadPort) -> None:
        """Получает read-порт внешнего tenant UoW."""
        self.read = read

    async def used(self, root_id: UUID, position_id: UUID | None = None) -> bool:
        """Учитывает все сохранённые группы без восстановления агрегатов."""
        return await self.read.used(root_id, position_id)
