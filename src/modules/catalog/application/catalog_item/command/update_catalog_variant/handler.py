from src.modules.catalog.application.catalog_item.command.update_catalog_variant.command import (
    UpdateCatalogVariantCommand,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_variant.dto import (
    UpdateCatalogVariantResultDTO,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateCatalogVariantHandler:
    """Проверяет внешние значения и делегирует изменение родительскому агрегату."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        schemas: CatalogItemContentSchemaPort,
        locales: LocalePort,
        currencies: CurrencyPort,
        sanitizer: RichTextSanitizerPort,
        files: CatalogImageFilesPort,
        clock: ClockPort,
    ) -> None:
        """Получает только порты и сервис записи общего tenant UoW."""
        self._mutations, self._schemas, self._locales = mutations, schemas, locales
        self._currencies, self._sanitizer, self._files, self._clock = (
            currencies,
            sanitizer,
            files,
            clock,
        )

    async def execute(
        self, command: UpdateCatalogVariantCommand
    ) -> UpdateCatalogVariantResultDTO:
        """Готовит кандидата с частичными переопределениями, не копируя parent."""
        root = await self._mutations.load(command.tenant_id, command.item_id)
        variant = root.variant(command.variant_id)
        locale = None
        schema = None
        content = None
        if command.fields & {"content", "gallery"}:
            if command.locale is None:
                raise InvalidCatalogValueError("Укажите locale.", ("content",))
            locale = LocaleVO(command.locale)
            await self._locales.ensure_active(locale.value)
        if "content" in command.fields and command.content is not None:
            schema = await self._schemas.get_by_id(root.product_type_id)
            if command.content.expected_schema_version != schema.schema_version:
                raise CatalogConflictError("Версия схемы изменилась.", ("content",))
            rich_codes = {b.code for b in schema.blocks if b.value_type == "rich_text"}
            content = {
                k: self._sanitizer.clean(v) if k in rich_codes else v
                for k, v in command.content.values.items()
            }
        if (
            "price_specification" in command.fields
            and command.price_specification is not None
        ):
            await self._currencies.ensure_active(command.price_specification.currency)
        if "gallery" in command.fields and command.gallery is not None:
            await self._files.ensure_images(
                command.tenant_id.uuid,
                tuple(i.file_id.uuid for i in command.gallery.images),
            )
        changed = variant.changed(
            fields=command.fields,
            actor=command.actor_id,
            now=self._clock.now(),
            status=command.status,
            sku=command.sku,
            virtual=command.virtual,
            price_specification=command.price_specification,
            stock=command.stock,
            weight=command.weight,
            dimensions=command.dimensions,
            locale=locale,
            content=content,
            gallery=command.gallery,
        )
        root.change_variant(
            variant=changed,
            actor=command.actor_id,
            now=self._clock.now(),
            schema=schema,
        )
        await self._mutations.save(root)
        return UpdateCatalogVariantResultDTO(changed.id.uuid)
