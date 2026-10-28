from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.entity.variant import CatalogVariant
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogVariantValues,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)
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
        if values.kind is CatalogItemKind.SIMPLE:
            if values.variants:
                raise InvalidCatalogValueError("Простой товар не содержит вариантов.")
            item = CatalogItem.create(
                CatalogItemIdVO(self.uuid.new()),
                actor_id,
                now,
                schema.id,
                values.virtual,
            )
        elif values.kind is CatalogItemKind.VARIABLE:
            if values.virtual or values.price_specification is not None:
                raise InvalidCatalogValueError("У контейнера нет цены и virtual.")
            item = CatalogItem.create_variable(
                identifier=CatalogItemIdVO(self.uuid.new()),
                actor=actor_id,
                now=now,
                product_type_id=schema.id,
            )
        else:
            raise InvalidCatalogValueError("Создавать вариант нужно через родителя.")
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
            status=CatalogItemStatus.DRAFT,
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
        for variant_values in values.variants:
            variant = await self.prepare_variant(
                tenant_id=tenant_id,
                actor_id=actor_id,
                parent=item,
                values=variant_values,
                schema=schema,
            )
            item.add_variant(variant=variant, actor=actor_id, now=now, schema=schema)
        item.update(
            fields=frozenset({"status"}), actor=actor_id, now=now, status=values.status
        )
        return item

    async def prepare_variant(
        self,
        *,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        parent: CatalogItem,
        values: CreateCatalogVariantValues,
        schema: ProductTypeSchemaSnapshot,
    ) -> CatalogVariant:
        """Проверяет внешние значения entity, не записывая унаследованные поля."""
        sku = SkuCodeVO(values.sku) if values.sku is not None else None
        if sku and await self.skus.in_use(sku.value):
            raise CatalogConflictError("SKU уже используется.", ("sku",))
        if values.price_specification:
            await self.currencies.ensure_active(values.price_specification.currency)
        now = self.clock.now()
        variant = CatalogVariant.create(
            identifier=CatalogItemIdVO(self.uuid.new()),
            parent_id=parent.id,
            actor=actor_id,
            now=now,
        )
        variant = variant.changed(
            fields=frozenset(
                {
                    "status",
                    "sku",
                    "virtual",
                    "price_specification",
                    "stock",
                    "weight",
                    "dimensions",
                }
            ),
            actor=actor_id,
            now=now,
            status=values.status,
            sku=sku,
            virtual=values.virtual,
            price_specification=values.price_specification,
            stock=values.stock,
            weight=values.weight,
            dimensions=values.dimensions,
        )
        rich_codes = {b.code for b in schema.blocks if b.value_type == "rich_text"}
        for code in sorted(values.translations.keys() | values.galleries.keys()):
            locale = LocaleVO(code)
            await self.locales.ensure_active(code)
            fields = set()
            content = None
            if code in values.translations:
                translation = values.translations[code]
                if translation.expected_schema_version not in (
                    None,
                    schema.schema_version,
                ):
                    raise CatalogConflictError("Версия схемы изменилась.", ("content",))
                fields.add("content")
                content = {
                    k: self.sanitizer.clean(v) if k in rich_codes else v
                    for k, v in translation.values.items()
                }
            gallery = values.galleries.get(code)
            if gallery is not None:
                fields.add("gallery")
                await self.files.ensure_images(
                    tenant_id.uuid, tuple(i.file_id.uuid for i in gallery.images)
                )
            variant = variant.changed(
                fields=frozenset(fields),
                actor=actor_id,
                now=now,
                locale=locale,
                content=content,
                gallery=gallery,
            )
        return variant
