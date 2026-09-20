from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyRequest(RequestModel):
    default_transaction_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    provider_code: Literal["NBU", "MANUAL"]
    rate_date_policy: Literal["exact", "previous_available"]
    rounding_mode: Literal["ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_UP"]
    allow_cross_rate: bool
    bridge_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    business_timezone: str = Field(min_length=1, max_length=64)


class ConfigureRequest(PolicyRequest):
    expected_version: int = Field(ge=1)


class InitializeRequest(PolicyRequest):
    enabled_currencies: list[str] = Field(min_length=1, max_length=200)
    functional_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    valid_from: date
    reason: str = Field(min_length=1, max_length=1000)


class EnabledRequest(RequestModel):
    enabled: bool


class ScheduleRequest(RequestModel):
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    effective_from: date
    reason: str = Field(min_length=1, max_length=1000)


class RateRequest(RequestModel):
    source_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    target_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    rate: str = Field(pattern=r"^\d+(\.\d+)?$", max_length=100)
    effective_date: date


class ConvertRequest(RequestModel):
    amount: str = Field(pattern=r"^-?\d+(\.\d+)?$", max_length=100)
    source_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    target_currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    business_date: date
    purpose: Literal["calculation", "booking", "display"] = "calculation"


class ActionResponse(BaseModel):
    ok: bool = True


class MoneyResponse(BaseModel):
    amount: str
    currency: str


class SnapshotResponse(BaseModel):
    source_currency: str
    target_currency: str
    rate: str
    requested_date: date
    effective_date: date
    converted_at: str
    provider_code: str
    derivation: str
    source_rate_ids: list[str]
    bridge_currency: str | None
    policy_version: int


class ConvertedMoneyResponse(BaseModel):
    original: MoneyResponse
    converted: MoneyResponse
    conversion: SnapshotResponse


class SettingsResponse(BaseModel):
    configured: bool
    policy: dict | None
    enabled_currencies: list[str]
    periods: list[dict]
    functional_currency: str | None
    future_functional_currency: str | None
    business_date: date
    provider_status: dict
    permissions: list[str]
