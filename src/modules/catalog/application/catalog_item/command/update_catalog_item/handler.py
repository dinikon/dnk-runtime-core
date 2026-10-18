from collections.abc import Awaitable
from typing import TypeVar
from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_item.dto import (
    UpdateCatalogItemResultDTO,
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
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogDependencyUnavailableError,
    InvalidCatalogValueError,
)
from src.modules.shared.domain.time.clock_port import ClockPort

T = TypeVar("T")


async def field_result(field: str, action: Awaitable[T]) -> T:
    """Привязывает отказ справочного порта к разделу без изменения бизнес-решения."""
    try:
        return await action
    except CatalogDependencyUnavailableError:
        raise
    except CatalogError as exc:
        raise InvalidCatalogValueError(str(exc), (field,)) from exc


class UpdateCatalogItemHandler:
    """Координирует единое редактирование под блокировкой одного товара."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        locales: LocalePort,
        schemas: CatalogItemContentSchemaPort,
        sanitizer: RichTextSanitizerPort,
        currencies: CurrencyPort,
        files: CatalogImageFilesPort,
    ) -> None:
        """Принимает порты одного внешнего tenant UoW, без управления транзакцией."""
        self._mutations = mutations
        self._clock = clock
        self._locales = locales
        self._schemas = schemas
        self._sanitizer = sanitizer
        self._currencies = currencies
        self._files = files

    async def execute(
        self, command: UpdateCatalogItemCommand
    ) -> UpdateCatalogItemResultDTO:
        """Загружает актуальное состояние, вызывает один domain update и сохраняет."""
        item = await self._mutations.load(command.tenant_id, command.item_id)
        localized = command.fields & {"content", "gallery"}
        locale = None
        if localized:
            if command.locale is None:
                raise InvalidCatalogValueError(
                    "Укажите locale.", tuple(sorted(localized))
                )
            locale = LocaleVO(command.locale)
            await field_result(
                sorted(localized)[0], self._locales.ensure_active(locale.value)
            )
        schema = None
        content = None
        if "content" in command.fields and command.content is not None:
            schema = await self._schemas.get_by_id(item.product_type_id)
            rich_codes = {
                block.code for block in schema.blocks if block.value_type == "rich_text"
            }
            content = {
                code: self._sanitizer.clean(value) if code in rich_codes else value
                for code, value in command.content.values.items()
            }
        if (
            "price_specification" in command.fields
            and command.price_specification is not None
        ):
            await field_result(
                "price_specification",
                self._currencies.ensure_active(command.price_specification.currency),
            )
        if "gallery" in command.fields and command.gallery is not None:
            await field_result(
                "gallery",
                self._files.ensure_images(
                    command.tenant_id.uuid,
                    tuple((i.file_id.uuid for i in command.gallery.images)),
                ),
            )
        item.update(
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
            schema=schema,
            expected_schema_version=(
                command.content.expected_schema_version if command.content else None
            ),
        )
        await self._mutations.save(item)
        return UpdateCatalogItemResultDTO(item.id.uuid)
