from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings


class NbuSettings(BaseModel):
    api_url: HttpUrl = "https://bank.gov.ua/NBU_Exchange/exchange_site"
    timeout_seconds: float = Field(default=15, gt=0, le=120)
    retry_count: int = Field(default=2, ge=0, le=5)
    sync_enabled: bool = True
    sync_schedule: str = "* * * * *"


class CurrencySettings(BaseModel):
    nbu: NbuSettings = Field(default_factory=NbuSettings)


class CurrencyConfig(BaseSettings):
    CURRENCY: CurrencySettings = Field(default_factory=CurrencySettings)
