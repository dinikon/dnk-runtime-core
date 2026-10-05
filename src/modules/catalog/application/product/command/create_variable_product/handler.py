from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
)
from src.modules.catalog.application.product.command.create_variable_product.dto import (
    CreatedVariableSelectionDTO,
    CreatedVariableVariantDTO,
    CreateVariableProductResultDTO,
)
from src.modules.catalog.application.product.port.attribute_reader import (
    AttributeReaderPort,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.aggregate import (
    Product,
    ProductVariant,
    VariantSelection,
)
from src.modules.catalog.domain.product.error import (
    ProductLocaleUnavailableError,
    ProductOptionUnavailableError,
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


class CreateVariableProductHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        skus: SkuReaderPort,
        attributes: AttributeReaderPort,
        locales: LocaleReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._skus = skus
        self._attributes = attributes
        self._locales = locales
        self._clock = clock
        self._uuids = uuids

    async def execute(
        self, command: CreateVariableProductCommand
    ) -> CreateVariableProductResultDTO:
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
        option_ids = await self._attributes.option_ids(
            frozenset(
                item.attribute_id
                for variant in command.variants
                for item in variant.selections
            )
        )
        for variant in command.variants:
            for item in variant.selections:
                if item.option_id not in option_ids.get(item.attribute_id, frozenset()):
                    raise ProductOptionUnavailableError(
                        "Product option does not belong to its attribute."
                    )
        sku_codes: dict = {}
        for variant in command.variants:
            if variant.sku_id not in sku_codes:
                code = await self._skus.get_code(variant.sku_id)
                if code is None:
                    raise ProductSkuNotFoundError("SKU not found.")
                sku_codes[variant.sku_id] = code
        variants = tuple(
            ProductVariant(
                id=VariantIdVO.from_value(self._uuids.new()),
                sku_id=EntityIdVO.from_value(item.sku_id),
                selections=tuple(
                    VariantSelection(
                        EntityIdVO.from_value(selection.attribute_id),
                        EntityIdVO.from_value(selection.option_id),
                    )
                    for selection in item.selections
                ),
            )
            for item in command.variants
        )
        product = Product.create_variable(
            product_id=ProductIdVO.from_value(self._uuids.new()),
            variants=variants,
            contents=contents,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(product)
        return CreateVariableProductResultDTO(
            id=product.id.uuid,
            type=product.type,
            variants=tuple(
                CreatedVariableVariantDTO(
                    id=item.id.uuid,
                    sku_id=item.sku_id.uuid,
                    sku_code=sku_codes[item.sku_id.uuid],
                    selections=tuple(
                        CreatedVariableSelectionDTO(
                            selection.attribute_id.uuid, selection.option_id.uuid
                        )
                        for selection in item.selections
                    ),
                )
                for item in product.variants
            ),
            content_locales=tuple(sorted(product.contents)),
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by.uuid,
            updated_by=product.updated_by.uuid,
        )
