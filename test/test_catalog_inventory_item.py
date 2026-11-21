from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.dto import (
    SetCatalogItemSkuResultDTO,
)

"""Связь Catalog/Inventory и доменный запрет удаления без инфраструктуры."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from pydantic import ValidationError

from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.command import (
    SetCatalogItemSkuCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.handler import (
    SetCatalogItemSkuHandler,
)
from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
)
from src.modules.catalog.application.catalog_item.inventory_service import (
    CatalogItemInventoryService,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.handler import (
    FindInventoryItemUsageHandler,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.entity.variant import CatalogVariant
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    CatalogNotFoundError,
    InvalidCatalogValueError,
)
from src.modules.catalog.infrastructure.catalog_item.inventory import (
    InventoryCatalogItems,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_sku import (
    SetCatalogItemSkuRequest,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.command import (
    DeleteInventoryItemCommand,
)
from src.modules.inventory.application.inventory_item.command.delete_inventory_item.handler import (
    DeleteInventoryItemHandler,
)
from src.modules.inventory.application.inventory_item.port.references import (
    InventoryItemReferenceDTO,
)
from src.modules.inventory.application.inventory_item.reference_service import (
    InventoryItemReferenceService,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemInUseError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.infrastructure.inventory_item.catalog_usage import (
    CatalogInventoryItemUsage,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from test.catalog_support import default_schema


class MemoryInventoryReferences:
    """Хранит полноценные настройки, чтобы обнаружить их случайный сброс при выборе."""

    def __init__(self) -> None:
        """Создаёт независимое хранилище полных агрегатов для проверки выбора SKU."""
        self.items: dict[UUID, InventoryItem] = {}

    async def lock(self, identifier: UUID) -> InventoryItemReferenceDTO | None:
        """Возвращает ссылку существующего агрегата."""
        item = self.items.get(identifier)
        return InventoryItemReferenceDTO(identifier, item.sku.value) if item else None

    async def find(self, sku: str) -> InventoryItemReferenceDTO | None:
        """Ищет точное совпадение, не создавая значение при частичном совпадении."""
        return next(
            (
                InventoryItemReferenceDTO(item.id.uuid, sku)
                for item in self.items.values()
                if item.sku.value == sku
            ),
            None,
        )

    async def get_for_update(
        self, identifier: InventoryItemIdVO
    ) -> InventoryItem | None:
        """Возвращает полный агрегат для команды назначения."""
        return self.items.get(identifier.uuid)

    async def get_by_sku_for_update(self, sku: SkuVO) -> InventoryItem | None:
        """Возвращает полное точное совпадение для команды создания."""
        return next((item for item in self.items.values() if item.sku == sku), None)

    async def add_if_absent(self, item: InventoryItem) -> bool:
        """Сохраняет только один агрегат с данным кодом."""
        if await self.find(item.sku.value):
            return False
        self.items[item.id.uuid] = item
        return True

    async def read(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[InventoryItemReferenceDTO, ...]:
        """Возвращает актуальные коды выбранных ссылок."""
        return tuple(
            InventoryItemReferenceDTO(identifier, self.items[identifier].sku.value)
            for identifier in identifiers
            if identifier in self.items
        )

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Фильтрует тестовый справочник по каноническому коду."""
        return tuple(
            identifier
            for identifier, item in self.items.items()
            if search in item.sku.value
        )


class CatalogInventoryItemTests(IsolatedAsyncioTestCase):
    """Проверяет сценарий через настоящие сервисы и доменные методы."""

    def setUp(self) -> None:
        """Собирает изолированные агрегаты и порты одного контекста."""
        self.now = datetime(2026, 11, 12, tzinfo=UTC)
        self.tenant, self.actor = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schema = default_schema()
        self.item = CatalogItem.create(
            CatalogItemIdVO(uuid4()), self.actor, self.now, self.schema.id
        )
        self.references = MemoryInventoryReferences()
        self.inventory = InventoryCatalogItems(
            InventoryItemReferenceService(
                self.references, self.references, UUID7Generator()
            )
        )
        self.links = AsyncMock(owner=AsyncMock(return_value=None))
        self.repository = AsyncMock(get=AsyncMock(return_value=self.item))
        self.mutations = CatalogItemMutationService(self.repository, AsyncMock())
        self.handler = SetCatalogItemSkuHandler(
            self.mutations,
            CatalogItemInventoryService(self.inventory, self.links),
            Mock(now=Mock(return_value=self.now)),
        )

    async def apply(
        self, selection: CatalogInventoryItemSelection
    ) -> SetCatalogItemSkuResultDTO:
        """Выполняет публичную команду для подготовленного корня."""
        return await self.handler.execute(
            SetCatalogItemSkuCommand(self.tenant, self.actor, self.item.id, selection)
        )

    async def test_default_creation_normalization_exact_match_and_repeat(self) -> None:
        """Новый код создаётся с defaults, повтор и изменение регистра не создают дубль."""
        result = await self.apply(
            CatalogInventoryItemSelection("create", sku=" Straße-01 ")
        )
        self.assertEqual(result.sku, "strasse-01")
        self.assertTrue(result.inventory_item_created)
        stored = self.references.items[result.inventory_item_id]
        self.assertEqual(
            (
                stored.base_uom.value,
                stored.quantity_rules.step,
                stored.tracking_mode.value,
                stored.expiration_mode.value,
                stored.barcodes,
                stored.packagings,
            ),
            ("PCS", Decimal("1"), "NONE", "NONE", (), ()),
        )
        self.assertEqual(self.item.inventory_item_id.uuid, stored.id.uuid)
        repeated = await self.apply(
            CatalogInventoryItemSelection("create", sku="STRASSE-01")
        )
        self.assertFalse(repeated.inventory_item_created)
        self.assertEqual(repeated.inventory_item_id, result.inventory_item_id)
        partial = await self.apply(
            CatalogInventoryItemSelection("create", sku="strasse")
        )
        self.assertNotEqual(partial.inventory_item_id, result.inventory_item_id)
        self.assertEqual(len(self.references.items), 2)

    async def test_busy_missing_and_invalid_selection_preserve_binding(self) -> None:
        """Ошибки выбора не меняют принятую связь и не вызывают сохранение."""
        first = await self.apply(
            CatalogInventoryItemSelection("create", sku="original")
        )
        before = self.item.snapshot()
        self.repository.save.reset_mock()
        self.links.owner.return_value = uuid4()
        with self.assertRaises(CatalogConflictError):
            await self.apply(
                CatalogInventoryItemSelection(
                    "existing", inventory_item_id=first.inventory_item_id
                )
            )
        with self.assertRaises(CatalogNotFoundError):
            await self.apply(
                CatalogInventoryItemSelection("existing", inventory_item_id=uuid4())
            )
        for code in ("", "x" * 26, "\u200bsku"):
            with self.assertRaises(InvalidCatalogValueError):
                await self.apply(CatalogInventoryItemSelection("create", sku=code))
        self.assertEqual(self.item.snapshot(), before)
        self.repository.save.assert_not_awaited()

    async def test_selection_preserves_settings_and_clear_preserves_inventory(
        self,
    ) -> None:
        """Выбор и отвязывание не редактируют настройки выбранного склада."""
        from dataclasses import replace
        from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
        from src.modules.inventory.domain.value_object.quantity_rules import (
            QuantityRulesVO,
        )

        stored = replace(
            InventoryItem.create(
                identifier=InventoryItemIdVO(uuid4()), sku=SkuVO("existing")
            ),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.001")),
        )
        self.references.items[stored.id.uuid] = stored
        result = await self.apply(
            CatalogInventoryItemSelection("existing", inventory_item_id=stored.id.uuid)
        )
        self.assertFalse(result.inventory_item_created)
        self.assertIs(self.references.items[stored.id.uuid], stored)
        cleared = await self.apply(CatalogInventoryItemSelection("clear"))
        self.assertIsNone(cleared.inventory_item_id)
        self.assertIsNone(self.item.inventory_item_id)
        self.assertIn(stored.id.uuid, self.references.items)

    async def test_variant_is_changed_through_root_and_variable_rejects_sku(
        self,
    ) -> None:
        """Контейнер не получает SKU, а вариант меняется только через свою семью."""
        root = CatalogItem.create_variable(
            identifier=self.item.id,
            actor=self.actor,
            now=self.now,
            product_type_id=self.schema.id,
        )
        self.repository.get.return_value = root
        with self.assertRaises(InvalidCatalogValueError):
            await self.apply(CatalogInventoryItemSelection("create", sku="container"))
        self.assertFalse(self.references.items)
        variant = CatalogVariant.create(
            identifier=CatalogItemIdVO(uuid4()),
            parent_id=root.id,
            actor=self.actor,
            now=self.now,
        )
        root.add_variant(
            variant=variant, actor=self.actor, now=self.now, schema=self.schema
        )
        result = await self.handler.execute(
            SetCatalogItemSkuCommand(
                self.tenant,
                self.actor,
                root.id,
                CatalogInventoryItemSelection("create", sku="variant"),
                variant.id,
            )
        )
        self.assertEqual(
            root.variant(variant.id).inventory_item_id.uuid, result.inventory_item_id
        )
        self.assertIsNone(root.inventory_item_id)

    async def test_delete_checks_public_usage_before_repository_delete(self) -> None:
        """Использование останавливает удаление в бизнес-логике до SQL DELETE."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()), sku=SkuVO("linked")
        )
        repository = AsyncMock(get_for_update=AsyncMock(return_value=item))
        links = AsyncMock(owner=AsyncMock(return_value=self.item.id.uuid))
        handler = DeleteInventoryItemHandler(
            repository, CatalogInventoryItemUsage(FindInventoryItemUsageHandler(links))
        )
        with self.assertRaises(InventoryItemInUseError):
            await handler.execute(DeleteInventoryItemCommand(item.id))
        repository.delete.assert_not_awaited()
        links.owner.assert_awaited_once_with(item.id.uuid)
        links.owner.return_value = None
        await handler.execute(DeleteInventoryItemCommand(item.id))
        repository.delete.assert_awaited_once_with(item)
        with self.assertRaises(InventoryItemInUseError):
            item.ensure_can_delete(InventoryItemDeletionUsage(True))

    def test_request_is_an_explicit_discriminated_selection(self) -> None:
        """Режимы не принимают неоднозначные поля, настройки Inventory или клиентские UUID создания."""
        for body in (
            {},
            {"mode": "existing", "sku": "x"},
            {"mode": "create", "sku": "x", "inventory_item_id": str(uuid4())},
            {"mode": "clear", "sku": None},
            {"mode": "create", "sku": 123},
            {"mode": "create", "sku": "x", "base_uom": "KG"},
        ):
            with self.subTest(body=body), self.assertRaises(ValidationError):
                SetCatalogItemSkuRequest.model_validate(body)
