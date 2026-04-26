from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.category.value_object import (
    CategoryIdVO,
    CategoryNameVO,
)


@dataclass(slots=True)
class CategoryEntity:
    """Доменная сущность категории товаров с self-reference parent."""

    id: CategoryIdVO
    created_at: datetime
    updated_at: datetime
    name: CategoryNameVO
    parent_category_id: CategoryIdVO | None = None

    @classmethod
    def create(
        cls,
        *,
        id_: CategoryIdVO,
        now: datetime,
        name: str,
        parent_category_id: CategoryIdVO | None = None,
    ) -> Self:
        """Создает категорию с едиными created_at/updated_at."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            name=CategoryNameVO(name),
            parent_category_id=parent_category_id,
        )

    def update(
        self,
        *,
        now: datetime,
        name: str,
        parent_category_id: CategoryIdVO | None = None,
    ) -> None:
        """Обновляет название и parent категории, если данные изменились."""
        new_name = CategoryNameVO(name)

        if self.name == new_name and self.parent_category_id == parent_category_id:
            return

        self.name = new_name
        self.parent_category_id = parent_category_id
        self.updated_at = now
