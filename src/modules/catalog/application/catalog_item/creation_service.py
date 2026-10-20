from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)
from src.modules.catalog.application.catalog_item.port.sku import CatalogItemSkuPort
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    CatalogError,
    CatalogDependencyUnavailableError,
    InvalidCatalogValueError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CatalogItemCreationService:
    """Готовит полностью проверенный агрегат для создания или предварительной проверки."""

    def __init__(
        self,
        schemas: CatalogItemContentSchemaPort,
        locales: LocalePort,
        currencies: CurrencyPort,
        skus: CatalogItemSkuPort,
        sanitizer: RichTextSanitizerPort,
        files: CatalogImageFilesPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает порты внешнего UoW; не сохраняет товар и не завершает транзакцию."""
        self.schemas, self.locales, self.currencies, self.skus = (
            schemas,
            locales,
            currencies,
            skus,
        )
        self.sanitizer, self.files, self.clock, self.uuid = (
            sanitizer,
            files,
            clock,
            uuid,
        )

    async def prepare(
        self,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        values: CreateCatalogItemValues,
    ) -> CatalogItem:
        """Проверяет внешние ссылки и применяет значения через фабрику и методы Domain."""
        schema = await self.schemas.get_by_code(values.product_type_code)
        sku = SkuCodeVO(values.sku) if values.sku is not None else None
        if sku and await self.skus.in_use(sku.value):
            raise CatalogConflictError("SKU уже используется.", ("sku",))
        if values.price_specification is not None:
            try:
                await self.currencies.ensure_active(values.price_specification.currency)
            except CatalogDependencyUnavailableError:
                raise
            except CatalogError as error:
                raise InvalidCatalogValueError(
                    str(error), ("price_specification",)
                ) from error
        now = self.clock.now()
        item = CatalogItem.create(
            CatalogItemIdVO(self.uuid.new()), actor_id, now, schema.id, values.virtual
        )
        item.update(
            fields=frozenset(
                (
                    "status",
                    "sku",
                    "price_specification",
                    "stock",
                    "weight",
                    "dimensions",
                )
            ),
            actor=actor_id,
            now=now,
            status=values.status,
            sku=sku,
            price_specification=values.price_specification,
            stock=values.stock,
            weight=values.weight,
            dimensions=values.dimensions,
        )
        rich_codes = {
            block.code for block in schema.blocks if block.value_type == "rich_text"
        }
        for code in sorted(values.translations.keys() | values.galleries.keys()):
            locale = LocaleVO(code)
            try:
                await self.locales.ensure_active(code)
            except CatalogDependencyUnavailableError:
                raise
            except CatalogError as error:
                raise InvalidCatalogValueError(str(error), ("translations",)) from error
            fields = set()
            content, version = None, None
            gallery = values.galleries.get(code)
            if code in values.translations:
                translation = values.translations[code]
                fields.add("content")
                content = {
                    key: self.sanitizer.clean(value) if key in rich_codes else value
                    for key, value in translation.values.items()
                }
                version = (
                    translation.expected_schema_version
                    if translation.expected_schema_version is not None
                    else schema.schema_version
                )
            if gallery is not None:
                fields.add("gallery")
                try:
                    await self.files.ensure_images(
                        tenant_id.uuid,
                        tuple(image.file_id.uuid for image in gallery.images),
                    )
                except CatalogDependencyUnavailableError:
                    raise
                except CatalogError as error:
                    raise InvalidCatalogValueError(
                        str(error), ("galleries",)
                    ) from error
            item.update(
                fields=frozenset(fields),
                actor=actor_id,
                now=now,
                locale=locale,
                content=content,
                gallery=gallery,
                schema=schema,
                expected_schema_version=version,
            )
        return item
