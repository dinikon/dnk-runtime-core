from typing import Protocol

from src.modules.inventory.application.product.dto import ProductFieldsDescriptionDTO
from src.modules.inventory.application.product.query.describe_product_fields_repository import (
    ProductFieldsDescriptionRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class DescribeProductFieldsUseCaseProtocol(Protocol):
    """Порт use case получения описания модели товара."""

    async def __call__(self, tenant_id: EntityIdVO) -> ProductFieldsDescriptionDTO:
        """Возвращает описание product и его полей для tenant."""
        ...


class DescribeProductFieldsUseCase:
    """Use case чтения описания runtime-модели product."""

    def __init__(
        self,
        repository: ProductFieldsDescriptionRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиторием описания product."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> ProductFieldsDescriptionDTO:
        """Возвращает описание объекта product и его полей."""
        return await self._repository.describe_fields(tenant_id=tenant_id)
