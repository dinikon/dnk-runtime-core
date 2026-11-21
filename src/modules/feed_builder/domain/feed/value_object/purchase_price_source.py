from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class PurchasePriceSourceVO:
    """Явно выбирает источник предложений, не вычисляя закупочную цену."""

    supplier_source_id: EntityIdVO

    def __post_init__(self) -> None:
        """Требует ссылку UUID; существование и права проверит Application."""
        if not isinstance(self.supplier_source_id, EntityIdVO):
            raise InvalidFeedValueError("Нужен идентификатор закупочного источника.")
