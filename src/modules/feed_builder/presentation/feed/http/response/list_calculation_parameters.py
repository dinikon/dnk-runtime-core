from pydantic import BaseModel


class CalculationParameterResponse(BaseModel):
    """Передаёт реализованный параметр, его тип и nullability."""

    id: str
    label: str
    value_type: str
    nullable: bool


class ListCalculationParametersResponse(BaseModel):
    """Передаёт закрытый реестр без неподключённых источников."""

    items: tuple[CalculationParameterResponse, ...]
