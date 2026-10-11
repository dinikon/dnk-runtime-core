from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_mapper import (
    CurrencyQueryMapper,
)
from src.modules.reference_data.infrastructure.persistence.models.currency import (
    CurrencyModel,
)


class SqlAlchemyCurrencyQueryRepository:
    """Читает одну активную валюту из public в общей транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW без собственного управления транзакцией."""
        self._session = session

    async def get_active(self, code: str) -> ValidateCurrencyResultDTO | None:
        """Возвращает проекцию активного кода без загрузки всего справочника."""
        currencies = CurrencyModel.__table__
        result = await self._session.execute(
            select(
                currencies.c.code, currencies.c.numeric_code, currencies.c.minor_units
            ).where(currencies.c.code == code, currencies.c.active.is_(True))
        )
        row = result.mappings().one_or_none()
        return None if row is None else CurrencyQueryMapper.to_validation(row)
