from src.modules.catalog.application.product.command.delete_product.command import (
    DeleteProductCommand,
)
from src.modules.catalog.application.product.command.delete_product.dto import (
    DeleteProductResultDTO,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol


class DeleteProductHandler:
    def __init__(self, repository: ProductRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, command: DeleteProductCommand) -> DeleteProductResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        await self._repository.delete(product)
        return DeleteProductResultDTO(product.id.uuid)
