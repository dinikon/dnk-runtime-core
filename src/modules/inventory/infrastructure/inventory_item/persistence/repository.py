from collections.abc import Mapping
from typing import Any
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemBarcodeAlreadyExistsError,
    InventoryItemNotFoundError,
    InventoryItemSkuAlreadyExistsError,
    InventoryItemInUseError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.mapper import (
    InventoryItemMapper,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)


class SqlAlchemyInventoryItemRepository:
    """Хранит полный агрегат на сессии внешнего UoW с выбранной tenant-схемой."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию процесса без владения её транзакцией."""
        self._session = session

    async def add(self, item: InventoryItem) -> None:
        """Вставляет корень и штрихкоды, переводя только известные unique-конфликты."""
        self._ensure_supported(item)
        try:
            await self._session.execute(
                insert(InventoryItemModel.__table__).values(
                    InventoryItemMapper.to_insert_values(item)
                )
            )
            barcodes = InventoryItemMapper.to_barcode_insert_values(item)
            if barcodes:
                await self._session.execute(
                    insert(ItemBarcodeModel.__table__), barcodes
                )
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def add_if_absent(self, item: InventoryItem) -> bool:
        """Сохраняет агрегат один раз без ошибки транзакции при гонке канонического SKU."""
        self._ensure_supported(item)
        table = InventoryItemModel.__table__
        try:
            identifier = await self._session.scalar(
                pg_insert(table)
                .values(InventoryItemMapper.to_insert_values(item))
                .on_conflict_do_nothing(constraint="uq_inventory_items_sku")
                .returning(table.c.id)
            )
            if identifier is None:
                return False
            barcodes = InventoryItemMapper.to_barcode_insert_values(item)
            if barcodes:
                await self._session.execute(
                    insert(ItemBarcodeModel.__table__), barcodes
                )
            return True
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def get_by_sku_for_update(self, sku: SkuVO) -> InventoryItem | None:
        """Проверяет точный код после ожидания конкурентного изменения или удаления."""
        table = InventoryItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(table.c.sku == sku.value).with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return await self._restore(row) if row is not None else None

    async def get_for_update(
        self, identifier: InventoryItemIdVO
    ) -> InventoryItem | None:
        """Блокирует корень первым, затем читает его штрихкоды в сохранённом порядке."""
        table = InventoryItemModel.__table__
        result = await self._session.execute(
            select(table).where(table.c.id == identifier.uuid).with_for_update()
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return await self._restore(row)

    async def _restore(self, row: Mapping[str, Any]) -> InventoryItem:
        """Читает дочерние данные уже заблокированного корня и делегирует mapping."""
        barcodes = ItemBarcodeModel.__table__
        children = await self._session.execute(
            select(barcodes)
            .where(barcodes.c.inventory_item_id == row["id"])
            .order_by(barcodes.c.position)
        )
        return InventoryItemMapper.to_domain(row, children.mappings().all())

    async def save(self, item: InventoryItem) -> None:
        """Обновляет корень по ID и атомарно заменяет дочерний состав с прежними ID."""
        self._ensure_supported(item)
        table = InventoryItemModel.__table__
        barcodes = ItemBarcodeModel.__table__
        try:
            result = await self._session.execute(
                update(table)
                .where(table.c.id == item.id.uuid)
                .values(InventoryItemMapper.to_update_values(item))
                .returning(table.c.id)
            )
            if result.scalar_one_or_none() is None:
                raise InventoryItemNotFoundError("Складская позиция не найдена.")
            await self._session.execute(
                delete(barcodes).where(barcodes.c.inventory_item_id == item.id.uuid)
            )
            children = InventoryItemMapper.to_barcode_insert_values(item)
            if children:
                await self._session.execute(insert(barcodes), children)
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def delete(self, item: InventoryItem) -> None:
        """Удаляет корень по ID; CASCADE затрагивает только собственные штрихкоды."""
        table = InventoryItemModel.__table__
        try:
            result = await self._session.execute(
                delete(table).where(table.c.id == item.id.uuid).returning(table.c.id)
            )
        except IntegrityError as exc:
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                exc.orig.__cause__, "constraint_name", None
            )
            if (
                self._sqlstate(exc) == "23503"
                and constraint == "fk_catalog_item_inventory_item"
            ):
                raise InventoryItemInUseError(
                    "Нельзя удалить складскую позицию: она связана с элементом каталога."
                ) from exc
            raise
        if result.scalar_one_or_none() is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")

    @staticmethod
    def _ensure_supported(item: InventoryItem) -> None:
        """Не допускает потери пока неподдерживаемых при хранении упаковок."""
        if item.packagings:
            raise RuntimeError("Хранение непустых упаковок пока не поддерживается.")

    @staticmethod
    def _sqlstate(error: IntegrityError) -> str | None:
        """Извлекает SQLSTATE из DBAPI-обёртки либо причины asyncpg."""
        return getattr(error.orig, "sqlstate", None) or getattr(
            error.orig.__cause__, "sqlstate", None
        )

    @staticmethod
    def _raise_unique_conflict(error: IntegrityError) -> None:
        """Преобразует именованные UNIQUE-ограничения, оставляя остальные ошибки наружу."""
        if SqlAlchemyInventoryItemRepository._sqlstate(error) != "23505":
            return
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            error.orig.__cause__, "constraint_name", None
        )
        if constraint == "uq_inventory_items_sku":
            raise InventoryItemSkuAlreadyExistsError(
                "SKU уже занят в текущем tenant."
            ) from error
        if constraint == "uq_inventory_item_barcodes_barcode":
            raise InventoryItemBarcodeAlreadyExistsError(
                "Штрихкод уже принадлежит складской позиции."
            ) from error
