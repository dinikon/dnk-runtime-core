from typing import Protocol

from src.modules.inventory.application.category.dto import CategoryFieldsDescriptionDTO
from src.modules.shared import EntityIdVO


class CategoryFieldsDescriptionRepositoryProtocol(Protocol):
    """Порт чтения описания runtime-модели категории товаров."""

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> CategoryFieldsDescriptionDTO:
        """Возвращает описание product_category и его полей для tenant."""
        ...


__all__ = ["CategoryFieldsDescriptionRepositoryProtocol"]
