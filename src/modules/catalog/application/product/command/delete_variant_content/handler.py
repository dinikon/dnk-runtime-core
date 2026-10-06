from src.modules.catalog.application.product.command.delete_variant_content.command import (
    DeleteVariantContentCommand,
)
from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class DeleteVariantContentHandler:
    def __init__(self, products: ProductRepositoryProtocol, clock: ClockPort) -> None:
        self._products, self._clock = products, clock

    async def execute(self, command: DeleteVariantContentCommand) -> None:
        product = await self._products.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        locale = ProductLocaleVO(command.locale)
        product.remove_variant_content(
            command.variant_id, locale, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._products.save_variant_content(product, command.variant_id, locale)
