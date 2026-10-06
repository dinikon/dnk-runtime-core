from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
)
from src.modules.catalog.application.product.command.create_variable_product.dto import (
    CreateVariableProductResultDTO,
)
from src.modules.catalog.application.content_schema.contracts import (
    ContentSchemaRepositoryProtocol,
)
from src.modules.catalog.application.content_schema.normalize_content import (
    RichTextSanitizerPort,
    normalize_content,
)
from src.modules.catalog.application.content_schema.service import SchemaNotFoundError
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.domain.product.aggregate import Product, ProductVariant
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
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


class CreateVariableProductHandler:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        skus: SkuReaderPort,
        locales: LocaleReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
        schemas: ContentSchemaRepositoryProtocol,
        sanitizer: RichTextSanitizerPort,
    ) -> None:
        self._repository, self._skus, self._locales, self._clock, self._uuids = (
            repository,
            skus,
            locales,
            clock,
            uuids,
        )
        self._schemas, self._sanitizer = schemas, sanitizer

    async def execute(
        self, command: CreateVariableProductCommand
    ) -> CreateVariableProductResultDTO:
        if len(command.sku_ids) < 2 or len(set(command.sku_ids)) != len(
            command.sku_ids
        ):
            raise InvalidProductVariantError(
                "VARIABLE requires at least two distinct SKUs."
            )
        for sku_id in command.sku_ids:
            if await self._skus.get_code(sku_id) is None:
                raise ProductSkuNotFoundError("SKU not found.")
        schema = await (
            self._schemas.get_type(command.product_type_id, lock=True)
            if command.product_type_id
            else self._schemas.get_clean_type()
        )
        if schema is None:
            raise SchemaNotFoundError("Product type not found.")
        contents = tuple(
            ProductContentVO(
                ProductLocaleVO(item.locale),
                normalize_content(
                    schema,
                    scope=ContentScope.PRODUCT,
                    version=command.schema_version or schema.schema_version,
                    blocks=item.blocks,
                    sanitizer=self._sanitizer,
                ),
            )
            for item in command.contents
        )
        for code in {item.locale.value for item in contents}:
            if not await self._locales.is_active(code):
                raise ProductLocaleUnavailableError("Product locale is not active.")
        variants = tuple(
            ProductVariant(
                VariantIdVO.from_value(self._uuids.new()), EntityIdVO.from_value(sku_id)
            )
            for sku_id in command.sku_ids
        )
        product = Product.create_variable(
            product_id=ProductIdVO.from_value(self._uuids.new()),
            product_type_id=ProductTypeIdVO.from_value(schema.id),
            variants=variants,
            contents=contents,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(product)
        return CreateVariableProductResultDTO(
            product.id.uuid,
            tuple(item.id.uuid for item in variants),
            schema.id,
            schema.schema_version,
        )
