from sqlalchemy import insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.warehouse.aggregate import Warehouse
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

    async def add(self, warehouse: Warehouse) -> None:
        """Добавляет карточку и переводит известный конфликт канонического кода."""
        try:
            await self._session.execute(
                insert(WarehouseModel).values(
                    WarehouseMapper.to_insert_values(warehouse)
                )
            )
        except IntegrityError as exc:
            self._raise_code_conflict(exc)
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
            self._raise_code_conflict(exc)
            raise
        if identifier is None:
            raise WarehouseNotFoundError("Склад не найден.")

    @staticmethod
    def _raise_code_conflict(error: IntegrityError) -> None:
        """Переводит только известный UNIQUE кода; остальные ошибки остаются техническими."""
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
