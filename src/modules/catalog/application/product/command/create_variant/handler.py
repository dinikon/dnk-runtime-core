from src.modules.catalog.application.product.command.create_variant.command import (
    CreateVariantCommand,
)
from src.modules.catalog.application.product.command.create_variant.dto import (
    CreateVariantResultDTO,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.aggregate import ProductVariant
from src.modules.catalog.domain.product.error import (
    ProductNotFoundError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.identifier import VariantIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CreateVariantHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        skus: SkuReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository, self._skus, self._clock, self._uuids = (
            repository,
            skus,
            clock,
            uuids,
        )

    async def execute(self, command: CreateVariantCommand) -> CreateVariantResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        code = await self._skus.get_code(command.sku_id)
        if code is None:
            raise ProductSkuNotFoundError("SKU not found.")
        variant = ProductVariant(
            VariantIdVO.from_value(self._uuids.new()),
            EntityIdVO.from_value(command.sku_id),
        )
        product.add_variant(variant, actor_id=command.actor_id, now=self._clock.now())
        await self._repository.save_variants(product)
        return CreateVariantResultDTO(
            variant.id.uuid, product.id.uuid, command.sku_id, code
        )
