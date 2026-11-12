from uuid import UUID

from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
    CatalogInventoryItemReference,
)
from src.modules.catalog.domain.error import (
    CatalogNotFoundError,
    InvalidCatalogValueError,
)
from src.modules.inventory.application.inventory_item.reference_service import (
    InventoryItemReferenceService,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError


class InventoryCatalogItems:
    """Адаптирует публичный Application-контракт Inventory без чтения его ORM."""

    def __init__(self, service: InventoryItemReferenceService) -> None:
        """Принимает сервис, собранный с Catalog на общей tenant-сессии."""
        self._service = service

    def normalize(self, sku: str) -> str:
        """Переводит проверку кода в предметную ошибку поля SKU каталога."""
        try:
            return self._service.normalize(sku)
        except InventoryError as exc:
            raise InvalidCatalogValueError(str(exc), ("sku",)) from exc

    async def resolve(
        self, selection: CatalogInventoryItemSelection
    ) -> CatalogInventoryItemReference | None:
        """Выполняет только явно выбранное действие без сброса существующих настроек."""
        try:
            if (
                selection.mode == "clear"
                and selection.inventory_item_id is None
                and selection.sku is None
            ):
                return None
            if (
                selection.mode == "existing"
                and selection.inventory_item_id is not None
                and selection.sku is None
            ):
                result = await self._service.select(selection.inventory_item_id)
            elif (
                selection.mode == "create"
                and selection.sku is not None
                and selection.inventory_item_id is None
            ):
                result = await self._service.get_or_create(selection.sku)
            else:
                raise InvalidCatalogValueError(
                    "Выберите существующий SKU, создание по коду или очистку.", ("sku",)
                )
            return CatalogInventoryItemReference(result.id, result.sku, result.created)
        except InventoryItemNotFoundError as exc:
            raise CatalogNotFoundError(str(exc), ("sku",)) from exc
        except InventoryError as exc:
            raise InvalidCatalogValueError(str(exc), ("sku",)) from exc

    async def find_id(self, sku: str) -> UUID | None:
        """Использует точное публичное чтение Inventory для импорта."""
        result = await self._service.find(self.normalize(sku))
        return result.id if result else None

    async def codes(self, identifiers: tuple[UUID, ...]) -> dict[UUID, str]:
        """Преобразует batch публичных ссылок в отображаемые коды."""
        return {row.id: row.sku for row in await self._service.read(identifiers)}

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Делегирует поиск кодов владельцу данных."""
        return await self._service.search_ids(search)
