from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    StockLocationNotFoundError,
    StockLocationCodeAlreadyExistsError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.stock_location.persistence.mapper import (
    StockLocationMapper,
)


class SqlAlchemyStockLocationRepository:
    """Читает и сохраняет самостоятельные локации на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(self, identifier: StockLocationIdVO) -> StockLocation | None:
        """Перечитывает родителя поверх identity map без загрузки его потомков."""
        statement = (
            select(StockLocationModel)
            .where(StockLocationModel.id == identifier.uuid)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockLocationMapper.to_domain(model) if model is not None else None

    async def add(self, location: StockLocation) -> None:
        """Вставляет адрес и переводит только известные конфликты UNIQUE и FK."""
        try:
            await self._session.execute(
                insert(StockLocationModel).values(
                    StockLocationMapper.to_insert_values(location)
                )
            )
        except IntegrityError as exc:
            self._raise_known_conflict(exc)
            raise

    async def get_for_update(
        self, identifier: StockLocationIdVO, *, warehouse_id: WarehouseIdVO
    ) -> StockLocation | None:
        """Блокирует и перечитывает адрес внутри склада поверх identity map."""
        statement = (
            select(StockLocationModel)
            .where(
                StockLocationModel.id == identifier.uuid,
                StockLocationModel.warehouse_id == warehouse_id.uuid,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockLocationMapper.to_domain(model) if model is not None else None

    async def save(self, location: StockLocation) -> None:
        """Обновляет три поля с проверкой ID и склада через RETURNING."""
        statement = (
            update(StockLocationModel)
            .where(
                StockLocationModel.id == location.id.uuid,
                StockLocationModel.warehouse_id == location.warehouse_id.uuid,
            )
            .values(StockLocationMapper.to_update_values(location))
            .returning(StockLocationModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            self._raise_known_conflict(exc)
            raise
        if identifier is None:
            raise StockLocationNotFoundError("Локация не найдена в указанном складе.")

    @staticmethod
    def _raise_known_conflict(error: IntegrityError) -> None:
        """Сохраняет причину предметного отказа; неизвестные ограничения не переводит."""
        cause = getattr(error.orig, "__cause__", None)
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(
            cause, "sqlstate", None
        )
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            cause, "constraint_name", None
        )
        if sqlstate == "23505" and constraint == "uq_stock_locations_warehouse_code":
            raise StockLocationCodeAlreadyExistsError(
                "Код локации уже занят в этом складе."
            ) from error
        if sqlstate == "23503" and constraint == "fk_stock_locations_warehouse":
            raise WarehouseNotFoundError("Склад не найден.") from error
        if sqlstate == "23503" and constraint == "fk_stock_locations_parent":
            raise StockLocationNotFoundError(
                "Родительская локация не найдена в указанном складе."
            ) from error
