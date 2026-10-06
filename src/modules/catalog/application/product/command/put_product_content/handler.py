from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.product.command.put_product_content.dto import (
    PutProductContentResultDTO,
)
from src.modules.catalog.application.content_schema.contracts import (
    ContentSchemaRepositoryProtocol,
)
from src.modules.catalog.application.content_schema.normalize_content import (
    RichTextSanitizerPort,
    normalize_content,
    content_by_code,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
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
        schemas: ContentSchemaRepositoryProtocol,
        sanitizer: RichTextSanitizerPort,
    ) -> None:
        self._repository = repository
        self._locales = locales
        self._clock = clock
        self._schemas = schemas
        self._sanitizer = sanitizer

    async def execute(
        self, command: PutProductContentCommand
    ) -> PutProductContentResultDTO:
        locale = ProductLocaleVO(command.locale)
        if not await self._locales.is_active(locale.value):
            raise ProductLocaleUnavailableError("Product locale is not active.")
        product = await self._repository.get_for_update(command.product_id)
        if product is None:
            raise ProductNotFoundError("Product not found.")
        schema = await self._schemas.get_type(product.product_type_id.uuid, lock=True)
        if schema is None:
            raise ProductNotFoundError("Product type not found.")
        content = ProductContentVO(
            locale,
            normalize_content(
                schema,
                scope=ContentScope.PRODUCT,
                version=command.schema_version,
                blocks=command.blocks,
                sanitizer=self._sanitizer,
            ),
        )
        product.replace_content(
            content, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._repository.save_content(product, locale)
        return PutProductContentResultDTO(
            product_id=product.id.uuid,
            locale=locale.value,
            schema_version=schema.schema_version,
            blocks=content_by_code(schema, ContentScope.PRODUCT, dict(content.values)),
            updated_at=product.updated_at,
            updated_by=product.updated_by.uuid,
        )
