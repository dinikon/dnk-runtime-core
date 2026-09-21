from pydantic import BaseModel


class DisplayCurrencyResponse(BaseModel):
    display_currency: str | None


__all__ = ["DisplayCurrencyResponse"]
