from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.application.feed.graph.input import FieldNodeInput


@dataclass(frozen=True, slots=True)
class PreviewFieldCalculationQuery:
    """Запрашивает диагностику текущего или несохранённого поля без записи состояния."""

    feed_id: FeedIdVO
    expected_version: int
    field_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None = None
    definition_override: FieldNodeInput | None = None
