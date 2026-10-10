from pydantic import BaseModel
from uuid import UUID


class GetVariantResponse(BaseModel):
    """Собственный результат get_variant с принадлежностью и источником Title."""

    id: UUID
    product_id: UUID
    kind: str
    revision: int
    schema_version: int
    selection: dict[str, str]
    content: dict[str, str] | None
    locales: tuple[str, ...]
    virtual: bool
    downloadable: bool
    effective_title: str | None
    title_source: str | None
