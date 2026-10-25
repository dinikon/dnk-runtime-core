from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DealCurrencyItemDTO:
    """Код и подпись валюты продажи."""

    code: str
    name: str


@dataclass(frozen=True, slots=True)
class ListDealCurrenciesResultDTO:
    """Конкретный результат валютного сценария."""

    items: tuple[DealCurrencyItemDTO, ...]
