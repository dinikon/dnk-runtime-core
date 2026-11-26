from uuid import UUID
from pydantic import Field
from src.modules.feed_builder.presentation.strict_request import ClosedSchema


class PublicationReferenceRequest(ClosedSchema):
    """Требует явную пару ID без произвольного раскрытия родителей."""

    catalog_item_id: UUID = Field(strict=False)
    catalog_variant_id: UUID | None = Field(default=None, strict=False)


class AddCatalogItemsRequest(ClosedSchema):
    """Принимает ограниченный атомарный пакет и версию Feed."""

    expected_feed_version: int = Field(ge=1, le=9223372036854775807)
    item_references: list[PublicationReferenceRequest] = Field(
        min_length=1, max_length=100
    )
