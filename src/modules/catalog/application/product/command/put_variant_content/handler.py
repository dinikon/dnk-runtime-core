from src.modules.catalog.application.product.command.put_variant_content.command import (
    PutVariantContentCommand,
)
from src.modules.catalog.application.product.command.put_variant_content.dto import (
    PutVariantContentResultDTO,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.domain.product.error import (
    ProductLocaleUnavailableError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class PutVariantContentHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        locales: LocaleReaderPort,
        clock: ClockPort,
    ) -> None:
        self._repository, self._locales, self._clock = repository, locales, clock

    async def execute(
        self, command: PutVariantContentCommand
    ) -> PutVariantContentResultDTO:
        locale = ProductLocaleVO(command.locale)
        if not await self._locales.is_active(locale.value):
            raise ProductLocaleUnavailableError("Product locale is not active.")
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        product.replace_variant_content(
            command.variant_id,
            locale,
            command.short_description,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.save_variant_content(product, command.variant_id, locale)
        return PutVariantContentResultDTO(
            command.variant_id.uuid,
            locale.value,
            product.get_variant(command.variant_id).contents[locale.value],
        )
