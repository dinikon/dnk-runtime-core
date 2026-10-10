from pydantic import BaseModel
from uuid import UUID


class GetAttributeOptionResponse(BaseModel):
    """Option в результате get_attribute, с подписью выбранной locale."""

    id: UUID
    code: str
    label: str | None
    position: int
    locales: tuple[str, ...]


class GetAttributeResponse(BaseModel):
    """Полный read-контракт сценария get_attribute."""

    id: UUID
    code: str
    value_type: str
    label: str | None
    revision: int
    locales: tuple[str, ...]
    options: tuple[GetAttributeOptionResponse, ...]
