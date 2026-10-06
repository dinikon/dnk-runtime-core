from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetVariantResultDTO:
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str
    requested_locale: str
    content_locales: tuple[str, ...]
    short_description: str | None
