from pydantic import BaseModel


class CountryResponse(BaseModel):
    code: str
    alpha3: str
    numeric_code: str
    name: str
