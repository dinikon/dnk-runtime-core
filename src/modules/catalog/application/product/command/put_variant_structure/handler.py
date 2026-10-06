from src.modules.catalog.application.product.command.put_variant_structure.command import (
    PutVariantStructureCommand,
)
from src.modules.catalog.application.product.command.put_variant_structure.dto import (
    PutVariantStructureResultDTO,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.aggregate import ProductVariant
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductNotFoundError,
    ProductSkuNotFoundError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.identifier import VariantIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PutVariantStructureHandler:
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

    async def execute(
        self, command: PutVariantStructureCommand
    ) -> PutVariantStructureResultDTO:
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        known = {item.id.uuid: item for item in product.variants}
        if len({item.id for item in command.variants if item.id is not None}) != sum(
            item.id is not None for item in command.variants
        ):
            raise InvalidProductVariantError("Duplicate variant identifier.")
        variants = []
        for item in command.variants:
            if item.id is not None and item.id not in known:
                raise ProductVariantNotFoundError("Variant not found in product.")
            if await self._skus.get_code(item.sku_id) is None:
                raise ProductSkuNotFoundError("SKU not found.")
            previous = known.get(item.id) if item.id else None
            variants.append(
                ProductVariant(
                    VariantIdVO.from_value(item.id or self._uuids.new()),
                    EntityIdVO.from_value(item.sku_id),
                    dict(previous.contents) if previous else {},
                )
            )
        product.replace_variant_structure(
            kind=command.kind,
            variants=tuple(variants),
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.save_variants(product)
        return PutVariantStructureResultDTO(
            product.id.uuid,
            product.kind,
            tuple(item.id.uuid for item in product.variants),
        )
