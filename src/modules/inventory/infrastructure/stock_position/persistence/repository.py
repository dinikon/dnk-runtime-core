from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.policy.receipt_serial_presence import (
    ReceiptSerialAlreadyPresentError,
)
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as Model,
)
from src.modules.inventory.infrastructure.stock_position.persistence.mapper import (
    StockPositionMapper,
)


class SqlAlchemyStockPositionRepository:
    """Блокирует позиции в общей tenant-сессии, не изменяя количество вне Domain."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает единственную сессию внешнего UoW."""
        self._session = session

    async def get_or_add_for_update(self, zero: StockPosition) -> StockPosition:
        """Атомарно создаёт отсутствующий ноль по NULLS NOT DISTINCT и перечитывает позицию."""
        statement = (
            pg_insert(Model)
            .values(StockPositionMapper.to_values(zero))
            .on_conflict_do_nothing(constraint="uq_stock_positions_dimensions")
        )
        await self._session.execute(statement)
        d = zero.dimensions
        statement_read = (
            select(Model)
            .where(
                Model.inventory_item_id == d.inventory_item_id.uuid,
                Model.location_id == d.location_id.uuid,
                Model.owner_id == d.owner_id.uuid,
                Model.stock_status == d.stock_status.value,
                Model.lot_id.is_not_distinct_from(d.lot_id.uuid if d.lot_id else None),
                Model.serial_id.is_not_distinct_from(
                    d.serial_id.uuid if d.serial_id else None
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement_read)).one()
        return StockPositionMapper.to_domain(model)

    async def save(self, position: StockPosition, *, expected_version: int) -> None:
        """Записывает доменный остаток с CAS и переводит только известный защитный индекс SERIAL."""
        statement = (
            update(Model)
            .where(Model.id == position.id.uuid, Model.version == expected_version)
            .values(on_hand_qty=position.on_hand_qty.value, version=position.version)
            .returning(Model.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            cause = getattr(exc.orig, "__cause__", None)
            state = getattr(exc.orig, "sqlstate", None) or getattr(
                cause, "sqlstate", None
            )
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            if state == "23505" and constraint == "uq_stock_positions_serial_positive":
                raise ReceiptSerialAlreadyPresentError(
                    "Экземпляр уже имеет положительный остаток."
                ) from exc
            raise
        if identifier is None:
            raise StockPositionVersionConflictError(
                "Версия физической позиции изменилась."
            )

    async def serial_presence(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[StockSerialPresenceSnapshot, ...]:
        """Читает все положительные позиции затронутых SERIAL без фильтра склада или владельца."""
        if not identifiers:
            return ()
        statement = (
            select(Model)
            .where(Model.serial_id.in_(identifiers), Model.on_hand_qty > 0)
            .order_by(Model.serial_id, Model.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(
            StockSerialPresenceSnapshot(
                StockSerialIdVO(identifier),
                tuple(
                    StockPositionMapper.to_domain(model).counting_snapshot()
                    for model in models
                    if model.serial_id == identifier
                ),
            )
            for identifier in identifiers
        )
