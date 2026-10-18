from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExchangeRateCurrencyDTO:
    """Сведения справочника для проверки котировки, без чужих доменных объектов."""

    code: str
    numeric_code: str | None
    is_metal: bool


class ExchangeRateCurrencyCatalogProtocol(Protocol):
    """Даёт активные валюты для набора кодов через публичный контракт справочника."""

    async def get_active(
        self, codes: tuple[str, ...]
    ) -> tuple[ExchangeRateCurrencyDTO, ...]:
        """Возвращает найденные активные записи для проверки снимка."""
        ...
