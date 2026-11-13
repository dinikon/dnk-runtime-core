from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.error import (
    WarehouseCodeAlreadyExistsError,
    WarehouseNotFoundError,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.warehouse.persistence.mapper import (
    WarehouseMapper,
)


class SqlAlchemyWarehouseRepository:
    """Записывает карточку склада на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию без владения транзакцией."""
        self._session = session

    async def get_for_share(self, identifier: WarehouseIdVO) -> Warehouse | None:
        """Согласует создание локаций с изменением склада, сохраняя параллельность чтений."""
        statement = (
            select(WarehouseModel)
            .where(WarehouseModel.id == identifier.uuid)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return WarehouseMapper.to_domain(model) if model is not None else None

    async def get_for_update(self, identifier: WarehouseIdVO) -> Warehouse | None:
        """Блокирует строку и перечитывает модель поверх кеша текущей сессии."""
        statement = (
            select(WarehouseModel)
            .where(WarehouseModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return WarehouseMapper.to_domain(model) if model is not None else None

    async def add(self, warehouse: Warehouse) -> None:
        """Добавляет карточку и переводит известный конфликт канонического кода."""
        try:
            await self._session.execute(
                insert(WarehouseModel).values(
                    WarehouseMapper.to_insert_values(warehouse)
                )
            )
        except IntegrityError as exc:
            self._raise_known_conflict(exc)
            raise

    async def save(self, warehouse: Warehouse) -> None:
        """Сохраняет существующий склад, проверяя ID через RETURNING."""
        statement = (
            update(WarehouseModel)
            .where(WarehouseModel.id == warehouse.id.uuid)
            .values(WarehouseMapper.to_update_values(warehouse))
            .returning(WarehouseModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            self._raise_known_conflict(exc)
            raise
        if identifier is None:
            raise WarehouseNotFoundError("Склад не найден.")

    @staticmethod
    def _raise_known_conflict(error: IntegrityError) -> None:
        """Переводит известные UNIQUE и FK основной локации, сохраняя неизвестные ошибки."""
        cause = getattr(error.orig, "__cause__", None)
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(
            cause, "sqlstate", None
        )
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            cause, "constraint_name", None
        )
        if sqlstate == "23505" and constraint == "uq_warehouses_code":
            raise WarehouseCodeAlreadyExistsError(
                "Код склада уже занят в текущем tenant."
            ) from error
        if (
            sqlstate == "23503"
            and constraint == "fk_warehouses_default_storage_location"
        ):
            raise StockLocationNotFoundError(
                "Основная локация не найдена в указанном складе."
            ) from error
