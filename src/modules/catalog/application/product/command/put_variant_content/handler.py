from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope

from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.error import CatalogConflictError
from src.modules.catalog.domain.product.error import VariantNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.command.put_variant_content.command import (
    PutVariantContentCommand,
)
from src.modules.catalog.application.product.command.put_variant_content.dto import (
    PutVariantContentResultDTO,
)


class PutVariantContentHandler:
    """Координирует put_variant_content; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        schemas: ProductSchemaService,
        locales: LocalePort,
        sanitizer: RichTextSanitizerPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._schemas = schemas
        self._locales = locales
        self._sanitizer = sanitizer

    async def execute(
        self, command: PutVariantContentCommand
    ) -> PutVariantContentResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        if product.variant.id != command.variant_id:
            raise VariantNotFoundError("Позиция отсутствует в Product.")
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        schema = await self._schemas.get(product.product_type_id)
        if schema.version != command.expected_schema_version:
            raise CatalogConflictError("Версия схемы изменилась.")
        values = dict(command.values)
        for block in schema.blocks:
            key = str(block.block_id)
            if (
                block.scope == ContentScope.VARIANT
                and block.value_type == ContentValueType.RICH_TEXT
                and key in values
            ):
                values[key] = self._sanitizer.clean(values[key])
        product.put_content(
            locale,
            values,
            schema,
            ContentScope.VARIANT,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(product)
        return PutVariantContentResultDTO(product.id.uuid, product.revision)
