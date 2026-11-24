from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.value_object.category_property import (
    CategoryScalar,
)


@dataclass(frozen=True, slots=True)
class CategoryNodeVO:
    """Хранит значения записи и ссылки в пределах поля."""

    id: UUID
    values: tuple[tuple[str, CategoryScalar], ...]
    parent_id: UUID | None = None
    catalog_id: UUID | None = None
    inherit_parent: bool = False

    def __post_init__(self) -> None:
        """Проверяет собственную идентичность и форму связей."""
        if (
            not isinstance(self.id, UUID)
            or self.parent_id is not None
            and not isinstance(self.parent_id, UUID)
            or self.catalog_id is not None
            and not isinstance(self.catalog_id, UUID)
            or type(self.inherit_parent) is not bool
            or self.inherit_parent
            and (self.catalog_id is None or self.parent_id is not None)
            or not isinstance(self.values, tuple)
            or len(self.values) != len(dict(self.values))
        ):
            raise InvalidFeedValueError("Некорректная запись категории.")
