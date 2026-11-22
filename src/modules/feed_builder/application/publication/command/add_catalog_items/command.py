from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)


@dataclass(frozen=True, slots=True)
class AddCatalogItemsCommand:
    """Передаёт фиксированный набор выбранных позиций и ожидаемую версию Feed."""

    feed_id: FeedIdVO
    expected_feed_version: int
    item_references: tuple[CatalogProductReferenceVO, ...]
