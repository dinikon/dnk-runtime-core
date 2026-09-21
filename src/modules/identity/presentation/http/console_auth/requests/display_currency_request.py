from pydantic import BaseModel, ConfigDict, Field


class DisplayCurrencyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_currency: str | None = Field(pattern=r"^[A-Za-z]{3}$")


__all__ = ["DisplayCurrencyRequest"]
