from pydantic import BaseModel


class LocaleResponse(BaseModel):
    code: str
    language_code: str
    script_code: str | None
    region_code: str | None
    country_code: str | None
    name: str
