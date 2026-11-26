from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class FeedSchemaVO:
    """Хранит полный упорядоченный снимок полей, включая пустую схему."""

    fields: tuple[FieldNodeDefinition, ...] = ()
    schema_format_version: int = 1
    category_trees: tuple[FeedCategoryTreeVO, ...] = ()

    def __post_init__(self) -> None:
        """Замораживает состав; уникальность полей обеспечивает корневой агрегат."""
        fields = sequence(self.fields, label="Feed fields", maximum=MAX_FIELDS)
        if (
            not all(isinstance(value, FieldNodeDefinition) for value in fields)
            or type(self.schema_format_version) is not int
            or self.schema_format_version not in (1, 2)
        ):
            raise InvalidFeedValueError(
                "Нужны FieldNodeDefinition и поддержанный формат схемы."
            )
        trees = sequence(
            self.category_trees, label="Feed category trees", maximum=MAX_FIELDS
        )
        if not all(isinstance(tree, FeedCategoryTreeVO) for tree in trees) or (
            trees and self.schema_format_version == 1
        ):
            raise InvalidFeedValueError("Деревья категорий доступны в графе версии 2.")
        object.__setattr__(self, "fields", fields)
        object.__setattr__(self, "category_trees", trees)
