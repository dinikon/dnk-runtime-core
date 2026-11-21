from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from uuid import UUID

from src.modules.inventory.application.inventory_item.port.references import (
    InventoryItemReferenceDTO,
    InventoryItemReferencesPort,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class InventoryItemReferenceService:
    """Публичный Application-контракт выбора и создания складской номенклатуры."""

    def __init__(
        self,
        repository: InventoryItemRepositoryProtocol,
        references: InventoryItemReferencesPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты одного внешнего UoW без инфраструктурных типов."""
        self._repository, self._references, self._uuid = repository, references, uuid

    def normalize(self, sku: str) -> str:
        """Проверяет код теми же правилами, что создание InventoryItem."""
        return SkuVO(sku).value

    async def find(self, sku: str) -> InventoryItemReferenceDTO | None:
        """Ищет точное совпадение без создания и изменения агрегата."""
        return await self._references.find(self.normalize(sku))

    async def select(self, identifier: UUID) -> InventoryItemReferenceDTO:
        """Выбирает существующую позицию и защищает её от конкурентного удаления."""
        result = await self._repository.get_for_update(
            InventoryItemIdVO.from_value(identifier)
        )
        if result is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        return InventoryItemReferenceDTO(result.id.uuid, result.sku.value)

    async def get_or_create(self, sku: str) -> InventoryItemReferenceDTO:
        """Создаёт только отсутствующий код с доменными настройками по умолчанию."""
        code = SkuVO(sku)
        existing = await self._repository.get_by_sku_for_update(code)
        if existing is not None:
            return InventoryItemReferenceDTO(existing.id.uuid, existing.sku.value)
        item = InventoryItem.create(
            identifier=InventoryItemIdVO.from_value(self._uuid.new()), sku=code
        )
        created = await self._repository.add_if_absent(item)
        if created:
            return InventoryItemReferenceDTO(item.id.uuid, item.sku.value, True)
        existing = await self._repository.get_by_sku_for_update(code)
        if existing is None:
            raise InventoryItemNotFoundError(
                "SKU был удалён во время назначения. Повторите выбор."
            )
        return InventoryItemReferenceDTO(existing.id.uuid, existing.sku.value)

    async def read(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[InventoryItemReferenceDTO, ...]:
        """Возвращает актуальные коды выбранных позиций одним batch."""
        return await self._references.read(identifiers)

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Передаёт поиск ссылок без ограничения первой страницей списка Inventory."""
        return await self._references.search_ids(search.strip().casefold())
