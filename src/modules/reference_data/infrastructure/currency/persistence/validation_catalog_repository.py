from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.dto import (
    GetCurrencyValidationCatalogRecordDTO,
)
from src.modules.reference_data.infrastructure.persistence.models.currency import (
    CurrencyModel,
)
from src.modules.reference_data.infrastructure.currency.persistence.validation_catalog_mapper import (
    CurrencyValidationCatalogQueryMapper,
)


class SqlAlchemyCurrencyValidationCatalogQueryRepository:
    """Читает запрошенные активные валюты одним SQL-запросом в public."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию внешнего UoW."""
        self._session = session

    async def get_active_codes(
        self, codes: tuple[str, ...]
    ) -> tuple[GetCurrencyValidationCatalogRecordDTO, ...]:
        """Возвращает batch DTO без собственного commit или чтения всего каталога."""
        if not codes:
            return ()
        table = CurrencyModel.__table__
        rows = (
            await self._session.execute(
                select(table.c.code, table.c.numeric_code, table.c.minor_units)
                .where(table.c.code.in_(codes), table.c.active.is_(True))
                .order_by(table.c.code)
            )
        ).mappings()
        return tuple(
            CurrencyValidationCatalogQueryMapper.to_validation_item(row) for row in rows
        )
