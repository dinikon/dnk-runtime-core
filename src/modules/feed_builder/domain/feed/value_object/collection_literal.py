from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.limits import MAX_COLLECTION_ITEMS
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class CollectionLiteralVO:
    """Хранит конечный однородный набор литералов условия, включая пустой."""

    kind: ClassVar[str] = "collection"
    item_type: LiteralValueType
    items: tuple[ScalarLiteralVO, ...]

    def __post_init__(self) -> None:
        """Копирует состав и проверяет совпадение типов всех элементов."""
        items = sequence(
            self.items, label="Collection literal", maximum=MAX_COLLECTION_ITEMS
        )
        if not isinstance(self.item_type, LiteralValueType) or any(
            not isinstance(item, ScalarLiteralVO) or item.value_type != self.item_type
            for item in items
        ):
            raise InvalidFeedValueError(
                "Коллекция должна содержать литералы одного типа."
            )
        object.__setattr__(self, "items", items)
