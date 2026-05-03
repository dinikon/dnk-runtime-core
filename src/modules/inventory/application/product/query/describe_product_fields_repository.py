from typing import Protocol

from src.modules.inventory.application.product.dto import ProductFieldsDescriptionDTO
from src.modules.shared import EntityIdVO


class ProductFieldsDescriptionRepositoryProtocol(Protocol):
    """Порт чтения описания runtime-модели товара."""

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> ProductFieldsDescriptionDTO:
        """Возвращает описание product и его полей для tenant."""
        ...


__all__ = ["ProductFieldsDescriptionRepositoryProtocol"]
