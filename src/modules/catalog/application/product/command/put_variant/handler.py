from src.modules.catalog.application.product.command.put_variant.command import (
    PutVariantCommand,
)
from src.modules.catalog.application.product.command.put_variant.dto import (
    PutVariantResultDTO,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.error import (
    ProductNotFoundError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PutVariantHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        skus: SkuReaderPort,
        clock: ClockPort,
    ) -> None:
        self._repository, self._skus, self._clock = repository, skus, clock

    async def execute(self, command: PutVariantCommand) -> PutVariantResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        code = await self._skus.get_code(command.sku_id)
        if code is None:
            raise ProductSkuNotFoundError("SKU not found.")
        product.change_variant_sku(
            command.variant_id,
            EntityIdVO.from_value(command.sku_id),
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.save_variants(product)
        return PutVariantResultDTO(
            command.variant_id.uuid, product.id.uuid, command.sku_id, code
        )
