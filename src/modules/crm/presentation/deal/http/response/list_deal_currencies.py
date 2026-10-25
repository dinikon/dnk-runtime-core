from pydantic import BaseModel


class DealCurrencyResponse(BaseModel):
    """Допустимая валюта CRM."""

    code: str
    name: str


class ListDealCurrenciesResponse(BaseModel):
    """Отдельный HTTP результат справочника."""

    items: tuple[DealCurrencyResponse, ...]
