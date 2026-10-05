from pydantic import BaseModel


class TimeZoneResponse(BaseModel):
    code: str
    country_codes: list[str]
