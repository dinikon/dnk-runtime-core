from typing import Protocol

from src.modules.inventory.application.category.command import UpdateCategoryCommand
from src.modules.inventory.application.category.dto import CategoryDTO
from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.service import CategoryService


class UpdateCategoryUseCaseProtocol(Protocol):
    """Порт use case обновления категории товаров."""

    async def __call__(self, command: UpdateCategoryCommand) -> CategoryDTO:
        """Обновляет категорию и возвращает DTO."""
        ...


class UpdateCategoryUseCase:
    """Use case обновления категории товаров через доменный сервис."""

    def __init__(self, service: CategoryService) -> None:
        """Инициализирует use case доменным сервисом категорий."""
        self._service = service

    async def __call__(self, command: UpdateCategoryCommand) -> CategoryDTO:
        """Выполняет команду обновления категории и мапит entity в DTO."""
        category = await self._service.update_category(
            tenant_id=command.tenant_id,
            category_id=command.category_id,
            name=command.name,
            parent_category_id=command.parent_category_id,
        )
        return self._to_dto(category)

    @staticmethod
    def _to_dto(category: CategoryEntity) -> CategoryDTO:
        """Мапит CategoryEntity в CategoryDTO."""
        return CategoryDTO(
            id=category.id.uuid,
            created_at=category.created_at,
            updated_at=category.updated_at,
            name=category.name.value,
            parent_category_id=(
                None
                if category.parent_category_id is None
                else category.parent_category_id.uuid
            ),
        )
