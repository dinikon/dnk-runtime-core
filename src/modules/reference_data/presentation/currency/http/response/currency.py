from pydantic import BaseModel


class CurrencyResponse(BaseModel):
    code: str
    numeric_code: str | None
    name: str
    minor_units: int | None
