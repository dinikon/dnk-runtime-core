from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)


@dataclass(frozen=True, slots=True)
class FeedCategoryTreeVO:
    """Хранит одну локальную таксономию в определении фида."""

    id: UUID
    settings: CategoryNodeDataVO

    def __post_init__(self) -> None:
        """Проверяет идентичность и структуру настроек дерева."""
        if not isinstance(self.id, UUID) or not isinstance(
            self.settings, CategoryNodeDataVO
        ):
            raise InvalidFeedValueError("Некорректное локальное дерево категорий.")
