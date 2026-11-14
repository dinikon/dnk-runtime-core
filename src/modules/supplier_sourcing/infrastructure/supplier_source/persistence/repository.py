from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierSourceNotFoundError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source_fulfillment_mode import (
    SupplierSourceFulfillmentModeModel,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.mapper import (
    SupplierSourceMapper,
)


class SqlAlchemySupplierSourceRepository:
    """Хранит целый агрегат на сессии внешнего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без управления транзакцией."""
        self._session = session

    async def add(self, source: SupplierSource) -> None:
        """Вставляет корень и его режимы атомарно."""
        await self._session.execute(
            insert(SupplierSourceModel).values(
                SupplierSourceMapper.to_insert_values(source)
            )
        )
        await self._write_modes(source)

    async def get_for_update(
        self, identifier: SupplierSourceIdVO
    ) -> SupplierSource | None:
        """Блокирует актуальный корень, затем загружает принадлежащие режимы."""
        statement = (
            select(SupplierSourceModel)
            .where(SupplierSourceModel.id == identifier.uuid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        statement_modes = (
            select(SupplierSourceFulfillmentModeModel)
            .where(SupplierSourceFulfillmentModeModel.supplier_source_id == model.id)
            .order_by(SupplierSourceFulfillmentModeModel.mode)
            .execution_options(populate_existing=True)
        )
        modes = (await self._session.scalars(statement_modes)).all()
        return SupplierSourceMapper.to_domain(model, modes)

    async def save(self, source: SupplierSource) -> None:
        """Обновляет существующий корень и заменяет его набор режимов."""
        statement = (
            update(SupplierSourceModel)
            .where(SupplierSourceModel.id == source.id.uuid)
            .values(SupplierSourceMapper.to_update_values(source))
            .returning(SupplierSourceModel.id)
        )
        if await self._session.scalar(statement) is None:
            raise SupplierSourceNotFoundError("Источник поставщика не найден.")
        await self._session.execute(
            delete(SupplierSourceFulfillmentModeModel).where(
                SupplierSourceFulfillmentModeModel.supplier_source_id == source.id.uuid
            )
        )
        await self._write_modes(source)

    async def _write_modes(self, source: SupplierSource) -> None:
        """Записывает непустой набор детей без отдельного репозитория."""
        values = SupplierSourceMapper.to_mode_insert_values(source)
        if values:
            await self._session.execute(
                insert(SupplierSourceFulfillmentModeModel), values
            )
