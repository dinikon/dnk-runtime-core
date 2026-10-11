from pydantic import BaseModel


class GetTenantCurrencySettingsResponse(BaseModel):
    """HTTP-ответ чтения неизменной базовой валюты текущего Tenant."""

    base_currency: str
