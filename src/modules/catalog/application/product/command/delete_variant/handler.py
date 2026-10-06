from src.modules.catalog.application.product.command.delete_variant.command import (
    DeleteVariantCommand,
)
from src.modules.catalog.application.product.command.delete_variant.dto import (
    DeleteVariantResultDTO,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class DeleteVariantHandler:
    def __init__(self, repository: ProductRepositoryProtocol, clock: ClockPort) -> None:
        self._repository, self._clock = repository, clock

    async def execute(self, command: DeleteVariantCommand) -> DeleteVariantResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        product.remove_variant(
            command.variant_id, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._repository.save_variants(product)
        return DeleteVariantResultDTO(product.id.uuid)
