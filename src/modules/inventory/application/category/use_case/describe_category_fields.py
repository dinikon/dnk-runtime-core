from typing import Protocol

from src.modules.inventory.application.category.dto import CategoryFieldsDescriptionDTO
from src.modules.inventory.application.category.query.describe_category_fields_repository import (
    CategoryFieldsDescriptionRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class DescribeCategoryFieldsUseCaseProtocol(Protocol):
    """Порт use case получения описания модели категории товаров."""

    async def __call__(self, tenant_id: EntityIdVO) -> CategoryFieldsDescriptionDTO:
        """Возвращает описание product_category и его полей для tenant."""
        ...


class DescribeCategoryFieldsUseCase:
    """Use case чтения описания runtime-модели product_category."""

    def __init__(
        self,
        repository: CategoryFieldsDescriptionRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиторием описания product_category."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> CategoryFieldsDescriptionDTO:
        """Возвращает описание объекта product_category и его полей."""
        return await self._repository.describe_fields(tenant_id=tenant_id)
