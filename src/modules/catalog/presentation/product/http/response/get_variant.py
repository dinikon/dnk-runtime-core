from uuid import UUID
from pydantic import BaseModel


class GetVariantResponse(BaseModel):
    """Ответ HTTP-сценария get_variant."""

    id: UUID
    product_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    virtual: bool
    downloadable: bool
