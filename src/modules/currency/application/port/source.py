from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SourceExchangeRateDTO:
    """Передаёт нормализованную запись внешнего источника для проверки справочника."""

    code: str
    numeric_code: str
    rate: Decimal


@dataclass(frozen=True, slots=True)
class SourceExchangeRateSnapshotDTO:
    """Передаёт весь ответ источника с единой датой действия."""

    effective_date: date
    quotes: tuple[SourceExchangeRateDTO, ...]


class ExchangeRateSourceProtocol(Protocol):
    """Получает снимок за явно заданную календарную дату без обращения к SQL."""

    async def fetch(self, effective_date: date) -> SourceExchangeRateSnapshotDTO:
        """Загружает и нормализует полный ответ источника."""
        ...
