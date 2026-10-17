from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Self
import re
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
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.product_type.value_object.schema import (
    DEFAULT_TYPE_ID,
    ProductTypeSchemaSnapshot,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
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
    attributes: tuple[EnumAttributeAssignmentVO, ...] = ()
    metadata: tuple[CatalogMetadataEntry, ...] = ()
    category_ids: tuple[EntityIdVO, ...] = ()
    primary_category_id: EntityIdVO | None = None
    tag_ids: tuple[EntityIdVO, ...] = ()

    @classmethod
    def create(
        cls,
        identifier: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
        virtual: bool = False,
    ) -> Self:
        """Создаёт самостоятельную позицию без скрытого варианта."""
        return cls.restore(
            identifier=identifier,
            product_type_id=DEFAULT_TYPE_ID,
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
        attributes: tuple[EnumAttributeAssignmentVO, ...] = (),
        metadata: tuple[CatalogMetadataEntry, ...] = (),
        category_ids: tuple[EntityIdVO, ...] = (),
        primary_category_id: EntityIdVO | None = None,
        tag_ids: tuple[EntityIdVO, ...] = (),
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
            attributes=attributes,
            metadata=metadata,
            category_ids=category_ids,
            primary_category_id=primary_category_id,
            tag_ids=tag_ids,
        )
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
            attributes=self.attributes,
            metadata=self.metadata,
            category_ids=self.category_ids,
            primary_category_id=self.primary_category_id,
            tag_ids=self.tag_ids,
        )

    def ensure_deletable(self, used: bool) -> None:
        """Запрещает удаление товара с внешними зависимостями."""
        if used:
            raise CatalogConflictError("Товар используется внешним модулем.")

    def _validate(self) -> None:
        """Проверяет итоговые инварианты самостоятельного товара."""
        if (
            not isinstance(self.id, CatalogItemIdVO)
            or not isinstance(self.created_by, EntityIdVO)
            or not isinstance(self.updated_by, EntityIdVO)
            or self.product_type_id != DEFAULT_TYPE_ID
            or not isinstance(self.status, CatalogItemStatus)
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность, схема или статус."
            )
        if any(
            v.tzinfo is None or v.utcoffset() is None
            for v in (self.created_at, self.updated_at)
        ):
            raise InvalidCatalogValueError("Audit требует timezone.")
        if self.sku is not None and not isinstance(self.sku, SkuCodeVO):
            raise InvalidCatalogValueError("Некорректный SKU.", ("sku",))
        if (
            len(set(self.category_ids)) != len(self.category_ids)
            or bool(self.category_ids) != (self.primary_category_id is not None)
            or (
                self.primary_category_id is not None
                and self.primary_category_id not in self.category_ids
            )
        ):
            raise InvalidCatalogValueError(
                "Нужны уникальные назначения и одна основная категория.",
                ("category_ids", "primary_category_id"),
            )
        if len(set(self.tag_ids)) != len(self.tag_ids):
            raise InvalidCatalogValueError("Метки должны быть уникальны.", ("tag_ids",))
        if type(self.virtual) is not bool:
            raise InvalidCatalogValueError("Virtual требует bool.", ("virtual",))
        if self.price is not None and not isinstance(self.price, PriceSpecificationVO):
            raise InvalidCatalogValueError(
                "Некорректная спецификация цены.", ("price_specification",)
            )
        if self.dimensions is not None and not isinstance(
            self.dimensions, DimensionsVO
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
        for locale, values in self.translations.items():
            LocaleVO(locale)
            self._validate_content(values)
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            self._validate_gallery(gallery)
        if len({a.attribute_id for a in self.attributes}) != len(
            self.attributes
        ) or len({a.position for a in self.attributes}) != len(self.attributes):
            raise InvalidCatalogValueError(
                "Атрибуты и позиции назначений уникальны.", ("attributes",)
            )
        image_ids = [
            image.id for gallery in self.galleries.values() for image in gallery.images
        ]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений уникальны во всех locale товара."
            )
        self._validate_metadata(self.metadata)

    @staticmethod
    def _validate_content(values: dict[str, str]) -> None:
        """Проверяет фиксированные блоки и обязательное непустое имя перевода."""
        if set(values) - {"name", "desc", "short_desc"}:
            raise InvalidCatalogValueError("Блок отсутствует в Default.", ("content",))
        if any(
            not isinstance(value, str) or len(value) > 1_000_000
            for value in values.values()
        ):
            raise InvalidCatalogValueError(
                "Контент требует текст до 1000000 символов.", ("content",)
            )
        if (
            "name" not in values
            or not values["name"].strip()
            or len(values["name"]) > 255
        ):
            raise InvalidCatalogValueError(
                "Name должен быть непустым текстом до 255 символов.", ("content",)
            )

    @staticmethod
    def _validate_gallery(gallery: CatalogItemGallery) -> None:
        """Проверяет идентичности, порядок и главное изображение всего набора."""
        images = gallery.images
        if (
            len(images) > 100
            or len({i.id for i in images}) != len(images)
            or len({i.file_id for i in images}) != len(images)
            or len({i.position for i in images}) != len(images)
            or any(
                type(i.position) is not int
                or i.position < 0
                or not isinstance(i.id, EntityIdVO)
                or not isinstance(i.file_id, EntityIdVO)
                or len(i.alt) > 1000
                or len(i.caption) > 5000
                for i in images
            )
        ):
            raise InvalidCatalogValueError(
                "Некорректный состав или порядок галереи.", ("gallery",)
            )
        if bool(images) != (gallery.primary_image_id is not None) or (
            images and gallery.primary_image_id not in {i.id for i in images}
        ):
            raise InvalidCatalogValueError(
                "Непустая галерея требует главное изображение из своего набора.",
                ("gallery",),
            )

    @staticmethod
    def _validate_metadata(values: tuple[CatalogMetadataEntry, ...]) -> None:
        """Проверяет канонические типы, порядок и запрет обхода полей карточки."""
        reserved = {
            "name",
            "desc",
            "short_desc",
            "sku",
            "price",
            "regular_price",
            "sale_price",
            "stock_quantity",
            "stock_status",
            "manage_stock",
            "virtual",
            "kind",
            "parent_id",
            "status",
            "weight",
            "dimensions",
            "product_type",
        }
        if len({v.key for v in values}) != len(values) or len(
            {v.position for v in values}
        ) != len(values):
            raise InvalidCatalogValueError(
                "Metadata key и position уникальны.", ("metadata",)
            )
        for v in values:
            if (
                not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.-]{0,63}", v.key)
                or v.key in reserved
                or v.position < 0
            ):
                raise InvalidCatalogValueError(
                    "Некорректный или зарезервированный metadata key.", ("metadata",)
                )
            if not (
                (v.value_type == "text" and isinstance(v.value, str))
                or (v.value_type == "boolean" and type(v.value) is bool)
                or (
                    v.value_type == "decimal"
                    and isinstance(v.value, Decimal)
                    and v.value.is_finite()
                    and v.value.as_tuple().exponent >= -6
                )
            ):
                raise InvalidCatalogValueError(
                    "Metadata принимает text/decimal/boolean.", ("metadata",)
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
        attributes: tuple[EnumAttributeAssignmentVO, ...] | None = None,
        metadata: tuple[CatalogMetadataEntry, ...] | None = None,
        category_ids: tuple[EntityIdVO, ...] | None = None,
        primary_category_id: EntityIdVO | None = None,
        tag_ids: tuple[EntityIdVO, ...] | None = None,
        definitions: tuple[EnumAttributeSnapshot, ...] = (),
        existing_categories: frozenset[EntityIdVO] = frozenset(),
        existing_tags: frozenset[EntityIdVO] = frozenset(),
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
            "attributes": attributes,
            "metadata": metadata,
            "category_ids": category_ids,
            "primary_category_id": primary_category_id,
            "tag_ids": tag_ids,
        }
        if not fields or fields - (values.keys() | {"content", "gallery"}):
            raise InvalidCatalogValueError("Нужны известные поля изменения.")
        for name in fields & {
            "status",
            "virtual",
            "stock",
            "attributes",
            "metadata",
            "category_ids",
            "tag_ids",
        }:
            if values[name] is None:
                raise InvalidCatalogValueError("Значение не может быть null.", (name,))
        changes = {
            ("price" if name == "price_specification" else name): value
            for name, value in values.items()
            if name in fields
        }
        if (
            "dimensions" in fields
            and isinstance(dimensions, DimensionsVO)
            and not any(
                value is not None
                for value in (dimensions.length, dimensions.width, dimensions.height)
            )
        ):
            changes["dimensions"] = None
        for name in fields & {"category_ids", "tag_ids"}:
            changes[name] = tuple(sorted(values[name], key=str))
        if "attributes" in fields:
            allowed = {d.id: d.option_ids for d in definitions}
            if any(
                a.attribute_id not in allowed
                or not set(a.option_ids).issubset(allowed[a.attribute_id])
                for a in attributes or ()
            ):
                raise InvalidCatalogValueError(
                    "Option отсутствует в определении.", ("attributes",)
                )
            changes["attributes"] = tuple(
                sorted(attributes or (), key=lambda a: a.position)
            )
        if "metadata" in fields:
            changes["metadata"] = tuple(
                sorted(metadata or (), key=lambda m: m.position)
            )
        if "category_ids" in fields and not set(category_ids or ()).issubset(
            existing_categories
        ):
            raise InvalidCatalogValueError(
                "Категория отсутствует в tenant.", ("category_ids",)
            )
        if "tag_ids" in fields and not set(tag_ids or ()).issubset(existing_tags):
            raise InvalidCatalogValueError("Метка отсутствует в tenant.", ("tag_ids",))
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
                        or schema.code != "default"
                        or schema.schema_version != expected_schema_version
                    ):
                        raise CatalogConflictError(
                            "Версия схемы изменилась.", ("content",)
                        )
                    translations[locale.value] = dict(content)
                changes["translations"] = translations
            if "gallery" in fields:
                galleries = dict(self.galleries)
                if gallery is None:
                    galleries.pop(locale.value, None)
                else:
                    galleries[locale.value] = gallery
                changes["galleries"] = galleries
        candidate = replace(self, **changes)
        if candidate != self:
            candidate.updated_by = actor
            candidate.updated_at = now
        candidate._validate()
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
