from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.product.command.put_product_content.dto import (
    PutProductContentResultDTO,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.domain.product.error import (
    ProductLocaleUnavailableError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class PutProductContentHandler:
    """Изменяет один перевод, сохраняя остальные части агрегата."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        locales: LocaleReaderPort,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._locales = locales
        self._clock = clock

    async def execute(
        self, command: PutProductContentCommand
    ) -> PutProductContentResultDTO:
        content = ProductContentVO(
            locale=ProductLocaleVO(command.locale),
            name=command.name,
            description=command.description,
        )
        if not await self._locales.is_active(content.locale.value):
            raise ProductLocaleUnavailableError("Product locale is not active.")
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        product.replace_content(
            content, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._repository.save_content(product, content.locale)
        return PutProductContentResultDTO(
            product_id=product.id.uuid,
            locale=content.locale.value,
            name=content.name,
            description=content.description,
            updated_at=product.updated_at,
            updated_by=product.updated_by.uuid,
        )
