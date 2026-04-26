from typing import Protocol

from src.modules.inventory.application.product.command import DeleteProductCommand
from src.modules.inventory.domain.product.service import ProductService


class DeleteProductUseCaseProtocol(Protocol):
    """Порт use case удаления товара."""

    async def __call__(self, command: DeleteProductCommand) -> None:
        """Удаляет товар tenant."""
        ...


class DeleteProductUseCase:
    """Use case удаления товара через доменный сервис."""

    def __init__(self, service: ProductService) -> None:
        """Инициализирует use case доменным сервисом товаров."""
        self._service = service

    async def __call__(self, command: DeleteProductCommand) -> None:
        """Выполняет команду удаления товара."""
        await self._service.delete_product(
            tenant_id=command.tenant_id,
            product_id=command.product_id,
        )
