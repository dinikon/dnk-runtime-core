from typing import Protocol

from src.modules.inventory.application.product.command import UpdateProductCommand
from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.domain.product.entity import ProductEntity
from src.modules.inventory.domain.product.service import ProductService


class UpdateProductUseCaseProtocol(Protocol):
    """Порт use case обновления товара."""

    async def __call__(self, command: UpdateProductCommand) -> ProductDTO:
        """Обновляет товар и возвращает DTO."""
        ...


class UpdateProductUseCase:
    """Use case обновления товара через доменный сервис."""

    def __init__(self, service: ProductService) -> None:
        """Инициализирует use case доменным сервисом товаров."""
        self._service = service

    async def __call__(self, command: UpdateProductCommand) -> ProductDTO:
        """Выполняет команду обновления товара и мапит entity в DTO."""
        product = await self._service.update_product(
            tenant_id=command.tenant_id,
            product_id=command.product_id,
            sku=command.sku,
            product_name=command.product_name,
            description=command.description,
            category_id=command.category_id,
        )
        return self._to_dto(product)

    @staticmethod
    def _to_dto(product: ProductEntity) -> ProductDTO:
        """Мапит ProductEntity в ProductDTO."""
        return ProductDTO(
            id=product.id.uuid,
            created_at=product.created_at,
            updated_at=product.updated_at,
            sku=product.sku.value,
            product_name=product.product_name.value,
            description=product.description,
            category_id=(
                None if product.category_id is None else product.category_id.uuid
            ),
        )
