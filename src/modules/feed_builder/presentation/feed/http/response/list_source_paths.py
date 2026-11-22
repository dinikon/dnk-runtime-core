from pydantic import BaseModel


class SourcePathResponse(BaseModel):
    """Передаёт закрытый источник и допустимые типы."""

    provider: str
    path: str
    label: str
    field_kinds: tuple[str, ...]
    requires_locale: bool


class ListSourcePathsResponse(BaseModel):
    """Передаёт разрешённые источники без данных товаров."""

    items: tuple[SourcePathResponse, ...]
