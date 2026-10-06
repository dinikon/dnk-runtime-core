from src.modules.catalog.application.product_type.command.delete_product_type.command import (
    DeleteProductTypeCommand,
)
from src.modules.catalog.application.product_type.command.delete_product_type.dto import (
    DeleteProductTypeResultDTO,
)
from src.modules.catalog.application.product_type.port.usage_reader import (
    ProductTypeUsageReaderPort,
)
from src.modules.catalog.domain.product_type.error import (
    ProductTypeConflictError,
    ProductTypeNotFoundError,
)
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)


class DeleteProductTypeHandler:
    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        usage: ProductTypeUsageReaderPort,
    ) -> None:
        self._repository, self._usage = repository, usage

    async def execute(
        self, command: DeleteProductTypeCommand
    ) -> DeleteProductTypeResultDTO:
        product_type = await self._repository.get_for_update(command.type_id)
        if product_type is None:
            raise ProductTypeNotFoundError("Product type not found.")
        if product_type.is_system or await self._usage.type_in_use(command.type_id):
            raise ProductTypeConflictError("Product type is system or in use.")
        await self._repository.delete(product_type)
        return DeleteProductTypeResultDTO(product_type.id.uuid)
