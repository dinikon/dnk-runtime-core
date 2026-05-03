from typing import Protocol

from src.modules.inventory.application.category.command import DeleteCategoryCommand
from src.modules.inventory.domain.category.service import CategoryService


class DeleteCategoryUseCaseProtocol(Protocol):
    """Порт use case удаления категории товаров."""

    async def __call__(self, command: DeleteCategoryCommand) -> None:
        """Удаляет категорию tenant."""
        ...


class DeleteCategoryUseCase:
    """Use case удаления категории товаров через доменный сервис."""

    def __init__(self, service: CategoryService) -> None:
        """Инициализирует use case доменным сервисом категорий."""
        self._service = service

    async def __call__(self, command: DeleteCategoryCommand) -> None:
        """Выполняет команду удаления категории."""
        await self._service.delete_category(
            tenant_id=command.tenant_id,
            category_id=command.category_id,
        )
