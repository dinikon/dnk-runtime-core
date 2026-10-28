from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Self
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.entity.variant import CatalogVariant
from src.modules.catalog.domain.catalog_item.policy.validation import (
    validate_content,
    validate_gallery,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    CatalogNotFoundError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class CatalogItem:
    """Самостоятельный товар с собственными значениями и жизненным циклом."""

    id: CatalogItemIdVO
    product_type_id: EntityIdVO
    status: CatalogItemStatus
    sku: SkuCodeVO | None
    virtual: bool
    price: PriceSpecificationVO | None
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    stock: StockSpecificationVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    translations: dict[str, dict[str, str]] = field(default_factory=dict)
    galleries: dict[str, CatalogItemGallery] = field(default_factory=dict)
    kind: CatalogItemKind = CatalogItemKind.SIMPLE
    variants: tuple[CatalogVariant, ...] = ()

    @classmethod
    def create(
        cls,
        identifier: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
        product_type_id: EntityIdVO,
        virtual: bool = False,
    ) -> Self:
        """Создаёт самостоятельную позицию без скрытого варианта."""
        return cls.restore(
            identifier=identifier,
            product_type_id=product_type_id,
            status=CatalogItemStatus.DRAFT,
            sku=None,
            virtual=virtual,
            price=None,
            weight=None,
            dimensions=None,
            stock=StockSpecificationVO(),
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: CatalogItemIdVO,
        product_type_id: EntityIdVO,
        status: CatalogItemStatus,
        sku: SkuCodeVO | None,
        virtual: bool,
        price: PriceSpecificationVO | None,
        weight: WeightVO | None,
        dimensions: DimensionsVO | None,
        stock: StockSpecificationVO,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        translations: dict[str, dict[str, str]] | None = None,
        galleries: dict[str, CatalogItemGallery] | None = None,
        schema: ProductTypeSchemaSnapshot | None = None,
        kind: CatalogItemKind = CatalogItemKind.SIMPLE,
        variants: tuple[CatalogVariant, ...] = (),
    ) -> Self:
        """Восстанавливает самостоятельный товар и проверяет его инварианты."""
        item = cls(
            id=identifier,
            product_type_id=product_type_id,
            status=status,
            sku=sku,
            virtual=virtual,
            price=price,
            weight=weight,
            dimensions=dimensions,
            stock=stock,
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
            translations={k: dict(v) for k, v in (translations or {}).items()},
            galleries=dict(galleries or {}),
            kind=kind,
            variants=tuple(variants),
        )
        item._validate()
        if item.translations or any(v.translations for v in item.variants):
            if schema is None or schema.id != product_type_id:
                raise InvalidCatalogValueError(
                    "Для восстановления контента нужна схема товара."
                )
            for values in item.translations.values():
                schema.validate_content(values)
        item._validate_variants(schema)
        return item

    @classmethod
    def create_variable(
        cls,
        *,
        identifier: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
        product_type_id: EntityIdVO,
    ) -> "CatalogItem":
        """Создаёт контейнер без продаваемого родителя и без скрытого варианта."""
        item = cls.create(identifier, actor, now, product_type_id)
        item.kind = CatalogItemKind.VARIABLE
        item._validate()
        return item

    def snapshot(self) -> CatalogItemValuesSnapshot:
        """Передаёт значения чистой политике без ссылки на агрегат."""
        return CatalogItemValuesSnapshot(
            id=self.id,
            product_type_id=self.product_type_id,
            status=self.status,
            sku=self.sku.value if self.sku else None,
            virtual=self.virtual,
            price=self.price,
            weight=self.weight,
            dimensions=self.dimensions,
            stock=self.stock,
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by,
            updated_by=self.updated_by,
            translations={k: dict(v) for k, v in self.translations.items()},
            galleries=dict(self.galleries),
            kind=self.kind,
        )

    def _validate(self) -> None:
        """Проверяет итоговые инварианты самостоятельного товара."""
        if (
            not isinstance(self.id, CatalogItemIdVO)
            or not isinstance(self.created_by, EntityIdVO)
            or not isinstance(self.updated_by, EntityIdVO)
            or not isinstance(self.product_type_id, EntityIdVO)
            or not isinstance(self.status, CatalogItemStatus)
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность, схема или статус."
            )
        if any(
            (
                v.tzinfo is None or v.utcoffset() is None
                for v in (self.created_at, self.updated_at)
            )
        ):
            raise InvalidCatalogValueError("Audit требует timezone.")
        if self.sku is not None and not isinstance(self.sku, SkuCodeVO):
            raise InvalidCatalogValueError("Некорректный SKU.", ("sku",))
        if type(self.virtual) is not bool:
            raise InvalidCatalogValueError("Virtual требует bool.", ("virtual",))
        if self.price is not None and (
            not isinstance(self.price, PriceSpecificationVO)
        ):
            raise InvalidCatalogValueError(
                "Некорректная спецификация цены.", ("price_specification",)
            )
        if self.dimensions is not None and (
            not isinstance(self.dimensions, DimensionsVO)
        ):
            raise InvalidCatalogValueError(
                "Размеры требуют значения с единицами.", ("dimensions",)
            )
        if self.weight is not None and not isinstance(self.weight, WeightVO):
            raise InvalidCatalogValueError(
                "Вес требует значение и единицу.", ("weight",)
            )
        if not isinstance(self.stock, StockSpecificationVO):
            raise InvalidCatalogValueError("Настройки наличия обязательны.", ("stock",))
        self._validate_variants()
        for locale, values in self.translations.items():
            LocaleVO(locale)
            validate_content(values)
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            validate_gallery(gallery)
        image_ids = [
            image.id for gallery in self.galleries.values() for image in gallery.images
        ]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений уникальны во всех locale товара."
            )

    def update(
        self,
        *,
        fields: frozenset[str],
        actor: EntityIdVO,
        now: datetime,
        status: CatalogItemStatus | None = None,
        sku: SkuCodeVO | None = None,
        virtual: bool | None = None,
        price_specification: PriceSpecificationVO | None = None,
        stock: StockSpecificationVO | None = None,
        weight: WeightVO | None = None,
        dimensions: DimensionsVO | None = None,
        locale: LocaleVO | None = None,
        content: dict[str, str] | None = None,
        gallery: CatalogItemGallery | None = None,
        schema: ProductTypeSchemaSnapshot | None = None,
        expected_schema_version: int | None = None,
    ) -> None:
        """Атомарно принимает явно заданные значения после проверки итогового кандидата."""
        values: dict[str, object] = {
            "status": status,
            "sku": sku,
            "virtual": virtual,
            "price_specification": price_specification,
            "stock": stock,
            "weight": weight,
            "dimensions": dimensions,
        }
        if not fields or fields - (values.keys() | {"content", "gallery"}):
            raise InvalidCatalogValueError("Нужны известные поля изменения.")
        for name in fields & {"status", "virtual", "stock"}:
            if values[name] is None:
                raise InvalidCatalogValueError("Значение не может быть null.", (name,))
        changes = {
            "price" if name == "price_specification" else name: value
            for name, value in values.items()
            if name in fields
        }
        if (
            "dimensions" in fields
            and isinstance(dimensions, DimensionsVO)
            and (
                not any(
                    (
                        value is not None
                        for value in (
                            dimensions.length,
                            dimensions.width,
                            dimensions.height,
                        )
                    )
                )
            )
        ):
            changes["dimensions"] = None
        if fields & {"content", "gallery"}:
            if not isinstance(locale, LocaleVO):
                raise InvalidCatalogValueError(
                    "Укажите locale локализованного раздела.",
                    tuple(sorted(fields & {"content", "gallery"})),
                )
            if "content" in fields:
                translations = {k: dict(v) for k, v in self.translations.items()}
                if content is None:
                    translations.pop(locale.value, None)
                else:
                    if (
                        schema is None
                        or schema.id != self.product_type_id
                        or (schema.schema_version != expected_schema_version)
                    ):
                        raise CatalogConflictError(
                            "Версия схемы изменилась.", ("content",)
                        )
                    schema.validate_content(content)
                    translations[locale.value] = dict(content)
                changes["translations"] = translations
            if "gallery" in fields:
                galleries = dict(self.galleries)
                if gallery is None:
                    galleries.pop(locale.value, None)
                else:
                    galleries[locale.value] = gallery
                changes["galleries"] = galleries
        if (
            "content" in fields
            and any(v.translations for v in self.variants)
            and schema is None
        ):
            raise InvalidCatalogValueError(
                "Для проверки наследуемого контента нужна схема.", ("content",)
            )
        candidate = replace(self, **changes)
        if candidate != self:
            candidate.updated_by = actor
            candidate.updated_at = now
        candidate._validate()
        candidate._validate_variants(schema)
        if candidate == self:
            return
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(candidate, name))

    def ensure_can_add_image(
        self,
        locale: LocaleVO,
        image: CatalogItemImage,
        main: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Проверяет добавление на отдельном кандидате до внешнего Files upload."""
        candidate = replace(self)
        candidate.add_image(locale, image, main, actor, now)

    def add_image(
        self,
        locale: LocaleVO,
        image: CatalogItemImage,
        main: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Добавляет изображение в набор, выбирая первое или явно главное."""
        gallery = self.galleries.get(locale.value)
        images = gallery.images if gallery else ()
        added = replace(
            image, position=max((i.position for i in images), default=-1) + 1
        )
        primary = image.id if main or not images else gallery.primary_image_id
        self.update(
            fields=frozenset({"gallery"}),
            locale=locale,
            gallery=CatalogItemGallery.create((*images, added), primary),
            actor=actor,
            now=now,
        )

    def _validate_variants(
        self, schema: ProductTypeSchemaSnapshot | None = None
    ) -> None:
        """Проверяет роли, принадлежность и согласованность всей семьи."""
        if not isinstance(self.kind, CatalogItemKind) or self.kind not in (
            CatalogItemKind.SIMPLE,
            CatalogItemKind.VARIABLE,
        ):
            raise InvalidCatalogValueError("Вариант не является корнем агрегата.")
        if self.kind is CatalogItemKind.SIMPLE and self.variants:
            raise InvalidCatalogValueError("Простой товар не содержит вариантов.")
        if self.kind is CatalogItemKind.VARIABLE:
            if self.price is not None or self.virtual:
                raise InvalidCatalogValueError("Контейнер не имеет цены и virtual.")
            if self.status is CatalogItemStatus.ACTIVE and not any(
                v.status is not CatalogItemStatus.ARCHIVED for v in self.variants
            ):
                raise InvalidCatalogValueError(
                    "Для Active нужен неархивный вариант.", ("status",)
                )
        identifiers = [self.id, *(v.id for v in self.variants)]
        if len(set(identifiers)) != len(identifiers):
            raise InvalidCatalogValueError(
                "Идентификаторы семьи должны быть уникальны."
            )
        skus = [
            value.value
            for value in (self.sku, *(v.sku for v in self.variants))
            if value is not None
        ]
        if len(set(skus)) != len(skus):
            raise CatalogConflictError("SKU уже используется в карточке.", ("sku",))
        image_ids = [
            i.id
            for item in (self, *self.variants)
            for g in item.galleries.values()
            for i in g.images
        ]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений семьи должны быть уникальны."
            )
        if schema is not None and schema.id != self.product_type_id:
            raise InvalidCatalogValueError(
                "Схема не принадлежит карточке.", ("content",)
            )
        for variant in self.variants:
            if variant.parent_id != self.id:
                raise InvalidCatalogValueError("Вариант принадлежит другому родителю.")
            variant.validate()
            if schema is not None:
                for locale, own in variant.translations.items():
                    effective = {**self.translations.get(locale, {}), **own}
                    schema.validate_content(effective)

    def variant(self, identifier: CatalogItemIdVO) -> CatalogVariant:
        """Возвращает только собственную entity или сообщает об отсутствии."""

        for variant in self.variants:
            if variant.id == identifier:
                return variant
        raise CatalogNotFoundError("Вариант отсутствует в карточке.")

    def add_variant(
        self,
        *,
        variant: CatalogVariant,
        actor: EntityIdVO,
        now: datetime,
        schema: ProductTypeSchemaSnapshot,
    ) -> None:
        """Атомарно добавляет полностью проверенный вариант."""
        if self.kind is not CatalogItemKind.VARIABLE:
            raise InvalidCatalogValueError("Варианты доступны только variable.")
        self._replace_variants((*self.variants, variant), actor, now, schema)

    def change_variant(
        self,
        *,
        variant: CatalogVariant,
        actor: EntityIdVO,
        now: datetime,
        schema: ProductTypeSchemaSnapshot | None = None,
    ) -> None:
        """Проверяет кандидата и заменяет только принадлежащую карточке позицию."""
        previous = self.variant(variant.id)
        if (
            variant.translations != previous.translations
            and variant.translations
            and schema is None
        ):
            raise InvalidCatalogValueError(
                "Для проверки контента варианта нужна схема.", ("content",)
            )
        self._replace_variants(
            tuple(variant if v.id == variant.id else v for v in self.variants),
            actor,
            now,
            schema,
        )

    def remove_variant(
        self, *, identifier: CatalogItemIdVO, actor: EntityIdVO, now: datetime
    ) -> None:
        """Удаляет entity с проверкой последнего варианта Active-карточки."""
        self.variant(identifier)
        self._replace_variants(
            tuple(v for v in self.variants if v.id != identifier), actor, now
        )

    def _replace_variants(
        self,
        variants: tuple[CatalogVariant, ...],
        actor: EntityIdVO,
        now: datetime,
        schema: ProductTypeSchemaSnapshot | None = None,
    ) -> None:
        """Проверяет полное кандидатное состояние до изменения агрегата."""
        candidate = replace(self, variants=variants)
        candidate._validate()
        candidate._validate_variants(schema)
        if candidate != self:
            self.variants = variants
            self.updated_by, self.updated_at = actor, now
