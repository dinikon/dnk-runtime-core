from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class CatalogItemImage:
    """Товарная ссылка на файл с собственным порядком и подписями locale."""

    id: EntityIdVO
    file_id: EntityIdVO
    position: int
    alt: str = ""
    caption: str = ""

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        file_id: EntityIdVO,
        position: int,
        alt: str = "",
        caption: str = "",
    ) -> Self:
        """Создаёт ссылку; итоговый состав и порядок проверяет CatalogItem."""
        return cls(identifier, file_id, position, alt, caption)

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        file_id: EntityIdVO,
        position: int,
        alt: str,
        caption: str,
    ) -> Self:
        """Восстанавливает ссылку без генерации нового ID."""
        return cls(identifier, file_id, position, alt, caption)
