from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductCommand,
)
from src.modules.catalog.application.product.command.create_product.dto import (
    CreateProductResultDTO,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.error import (
    ProductLocaleUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CreateProductHandler:
    """Создаёт SIMPLE в одной внешней транзакции с проверками ссылок."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        skus: SkuReaderPort,
        locales: LocaleReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._skus = skus
        self._locales = locales
        self._clock = clock
        self._uuids = uuids

    async def execute(self, command: CreateProductCommand) -> CreateProductResultDTO:
        sku_code = await self._skus.get_code(command.sku_id)
        if sku_code is None:
            raise ProductSkuNotFoundError("SKU not found.")
        contents = tuple(
            ProductContentVO(
                locale=ProductLocaleVO(item.locale),
                name=item.name,
                description=item.description,
            )
            for item in command.contents
        )
        for code in {item.locale.value for item in contents}:
            if not await self._locales.is_active(code):
                raise ProductLocaleUnavailableError("Product locale is not active.")
        product = Product.create(
            product_id=ProductIdVO.from_value(self._uuids.new()),
            variant_id=VariantIdVO.from_value(self._uuids.new()),
            sku_id=EntityIdVO.from_value(command.sku_id),
            contents=contents,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(product)
        return CreateProductResultDTO(
            id=product.id.uuid,
            kind=product.kind,
            variant_id=product.variant.id.uuid,
            sku_id=product.variant.sku_id.uuid,
            sku_code=sku_code,
            content_locales=tuple(sorted(product.contents)),
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by.uuid,
            updated_by=product.updated_by.uuid,
        )
