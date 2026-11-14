from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InventoryItemBarcodeAlreadyExistsError,
    InventoryItemNotFoundError,
    InventoryItemSkuAlreadyExistsError,
    InventoryItemInUseError,
    InventoryItemConflictError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.infrastructure.inventory_item.persistence.mapper import (
    InventoryItemMapper,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)


class SqlAlchemyInventoryItemRepository:
    """Хранит полный агрегат на сессии внешнего UoW с выбранной tenant-схемой."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию процесса без владения её транзакцией."""
        self._session = session

    async def add(self, item: InventoryItem) -> None:
        """Вставляет корень, упаковки и штрихкоды, переводя только известные unique-конфликты."""
        try:
            await self._session.execute(
                insert(InventoryItemModel).values(
                    InventoryItemMapper.to_insert_values(item)
                )
            )
            barcodes = InventoryItemMapper.to_barcode_insert_values(item)
            if barcodes:
                await self._session.execute(insert(ItemBarcodeModel), barcodes)
            packagings = InventoryItemMapper.to_packaging_insert_values(item)
            if packagings:
                await self._session.execute(insert(ItemPackagingModel), packagings)
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def add_if_absent(self, item: InventoryItem) -> bool:
        """Сохраняет агрегат один раз без ошибки транзакции при гонке канонического SKU."""
        statement = (
            pg_insert(InventoryItemModel)
            .values(InventoryItemMapper.to_insert_values(item))
            .on_conflict_do_nothing(constraint="uq_inventory_items_sku")
            .returning(InventoryItemModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
            if identifier is None:
                return False
            barcodes = InventoryItemMapper.to_barcode_insert_values(item)
            if barcodes:
                await self._session.execute(insert(ItemBarcodeModel), barcodes)
            packagings = InventoryItemMapper.to_packaging_insert_values(item)
            if packagings:
                await self._session.execute(insert(ItemPackagingModel), packagings)
            return True
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def get_by_sku_for_update(self, sku: SkuVO) -> InventoryItem | None:
        """Блокирует точный код и перечитывает состояние ранее загруженной ORM-модели."""
        statement = (
            select(InventoryItemModel)
            .where(InventoryItemModel.sku == sku.value)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return await self._restore(model) if model is not None else None

    async def get_for_update(
        self, identifier: InventoryItemIdVO
    ) -> InventoryItem | None:
        """Блокирует и перечитывает корень, затем читает обе дочерние коллекции в сохранённом порядке."""
        statement = (
            select(InventoryItemModel)
            .where(InventoryItemModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        return await self._restore(model)

    async def _restore(self, model: InventoryItemModel) -> InventoryItem:
        """Читает дочерние данные уже заблокированного корня и делегирует mapping."""
        statement = (
            select(ItemBarcodeModel)
            .where(ItemBarcodeModel.inventory_item_id == model.id)
            .order_by(ItemBarcodeModel.position)
            .execution_options(populate_existing=True)
        )
        children = (await self._session.scalars(statement)).all()
        statement = (
            select(ItemPackagingModel)
            .where(ItemPackagingModel.inventory_item_id == model.id)
            .order_by(ItemPackagingModel.position, ItemPackagingModel.id)
            .execution_options(populate_existing=True)
        )
        packagings = (await self._session.scalars(statement)).all()
        return InventoryItemMapper.to_domain(model, children, packagings)

    async def save(self, item: InventoryItem) -> None:
        """Обновляет корень по ID и атомарно заменяет дочерний состав с прежними ID."""
        statement = (
            update(InventoryItemModel)
            .where(InventoryItemModel.id == item.id.uuid)
            .values(InventoryItemMapper.to_update_values(item))
            .returning(InventoryItemModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
            if identifier is None:
                raise InventoryItemNotFoundError("Складская позиция не найдена.")
            await self._session.execute(
                delete(ItemBarcodeModel).where(
                    ItemBarcodeModel.inventory_item_id == item.id.uuid
                )
            )
            children = InventoryItemMapper.to_barcode_insert_values(item)
            if children:
                await self._session.execute(insert(ItemBarcodeModel), children)
            await self._session.execute(
                delete(ItemPackagingModel).where(
                    ItemPackagingModel.inventory_item_id == item.id.uuid
                )
            )
            packagings = InventoryItemMapper.to_packaging_insert_values(item)
            if packagings:
                await self._session.execute(insert(ItemPackagingModel), packagings)
        except IntegrityError as exc:
            self._raise_unique_conflict(exc)
            raise

    async def delete(self, item: InventoryItem) -> None:
        """Удаляет корень по ID; CASCADE затрагивает собственные упаковки и штрихкоды."""
        statement = (
            delete(InventoryItemModel)
            .where(InventoryItemModel.id == item.id.uuid)
            .returning(InventoryItemModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            cause = getattr(exc.orig, "__cause__", None)
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            if (
                self._sqlstate(exc) == "23503"
                and constraint == "fk_catalog_item_inventory_item"
            ):
                raise InventoryItemInUseError(
                    "Нельзя удалить складскую позицию: она связана с элементом каталога."
                ) from exc
            if (
                self._sqlstate(exc) in {"23503", "23001"}
                and constraint == "fk_stock_lots_item"
            ):
                raise InventoryItemInUseError(
                    "Нельзя удалить складскую позицию: у неё есть партии."
                ) from exc
            raise
        if identifier is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")

    @staticmethod
    def _sqlstate(error: IntegrityError) -> str | None:
        """Извлекает SQLSTATE из DBAPI-обёртки либо причины asyncpg."""
        cause = getattr(error.orig, "__cause__", None)
        return getattr(error.orig, "sqlstate", None) or getattr(cause, "sqlstate", None)

    @staticmethod
    def _raise_unique_conflict(error: IntegrityError) -> None:
        """Преобразует именованные UNIQUE-ограничения, оставляя остальные ошибки наружу."""
        if SqlAlchemyInventoryItemRepository._sqlstate(error) != "23505":
            return
        cause = getattr(error.orig, "__cause__", None)
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            cause, "constraint_name", None
        )
        if constraint == "uq_inventory_items_sku":
            raise InventoryItemSkuAlreadyExistsError(
                "SKU уже занят в текущем tenant."
            ) from error
        if constraint == "uq_inventory_item_barcodes_barcode":
            raise InventoryItemBarcodeAlreadyExistsError(
                "Штрихкод уже принадлежит складской позиции."
            ) from error
        if constraint == "uq_item_packagings_code":
            raise InventoryItemConflictError(
                "Код упаковки уже занят внутри товара."
            ) from error
