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
    revision: int
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
    def create_simple(
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
            revision=1,
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
        revision: int,
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
            revision=revision,
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
            revision=self.revision,
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

    def ensure_revision(self, expected: int) -> None:
        """Отклоняет запись по устаревшей ревизии товара."""
        if type(expected) is not int or expected != self.revision:
            raise CatalogConflictError(
                "Ревизия товара изменилась. Загрузите актуальные данные."
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
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность, схема, статус или ревизия."
            )
        if any(
            v.tzinfo is None or v.utcoffset() is None
            for v in (self.created_at, self.updated_at)
        ):
            raise InvalidCatalogValueError("Audit требует timezone.")
        if self.sku is not None and not isinstance(self.sku, SkuCodeVO):
            raise InvalidCatalogValueError("Некорректный SKU.")
        if (
            len(set(self.category_ids)) != len(self.category_ids)
            or bool(self.category_ids) != (self.primary_category_id is not None)
            or (
                self.primary_category_id is not None
                and self.primary_category_id not in self.category_ids
            )
            or len(set(self.tag_ids)) != len(self.tag_ids)
        ):
            raise InvalidCatalogValueError(
                "Нужны уникальные назначения и одна основная категория."
            )
        if type(self.virtual) is not bool:
            raise InvalidCatalogValueError("Virtual требует bool.")
        if self.price is not None and not isinstance(self.price, PriceSpecificationVO):
            raise InvalidCatalogValueError("Некорректная спецификация цены.")
        if self.dimensions is not None and not isinstance(
            self.dimensions, DimensionsVO
        ):
            raise InvalidCatalogValueError("Размеры требуют значения с единицами.")
        if self.weight is not None and not isinstance(self.weight, WeightVO):
            raise InvalidCatalogValueError("Вес требует значение и единицу.")
        if not isinstance(self.stock, StockSpecificationVO):
            raise InvalidCatalogValueError("Настройки наличия обязательны.")
        for locale, values in self.translations.items():
            LocaleVO(locale)
            self._validate_content(values)
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            self._validate_gallery(gallery)
        if len({a.attribute_id for a in self.attributes}) != len(
            self.attributes
        ) or len({a.position for a in self.attributes}) != len(self.attributes):
            raise InvalidCatalogValueError("Атрибуты и позиции назначений уникальны.")
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
            raise InvalidCatalogValueError("Блок отсутствует в Default.")
        if any(
            not isinstance(value, str) or len(value) > 1_000_000
            for value in values.values()
        ):
            raise InvalidCatalogValueError("Контент требует текст до 1000000 символов.")
        if (
            "name" not in values
            or not values["name"].strip()
            or len(values["name"]) > 255
        ):
            raise InvalidCatalogValueError(
                "Name должен быть непустым текстом до 255 символов."
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
            raise InvalidCatalogValueError("Некорректный состав или порядок галереи.")
        if bool(images) != (gallery.primary_image_id is not None) or (
            images and gallery.primary_image_id not in {i.id for i in images}
        ):
            raise InvalidCatalogValueError(
                "Непустая галерея требует главное изображение из своего набора."
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
            raise InvalidCatalogValueError("Metadata key и position уникальны.")
        for v in values:
            if (
                not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.-]{0,63}", v.key)
                or v.key in reserved
                or v.position < 0
            ):
                raise InvalidCatalogValueError(
                    "Некорректный или зарезервированный metadata key."
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
                    "Metadata принимает text/decimal/boolean."
                )

    def _change(self, actor: EntityIdVO, now: datetime, **changes: object) -> None:
        """Проверяет кандидат до принятия нового состояния и увеличения ревизии."""
        candidate = replace(
            self,
            **changes,
            revision=self.revision + 1,
            updated_by=actor,
            updated_at=now,
        )
        candidate._validate()
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(candidate, name))

    def set_status(
        self,
        status: CatalogItemStatus,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет локальный статус, с проверкой ревизии товара."""
        self._change(actor, now, status=status)

    def set_sku(
        self,
        sku: SkuCodeVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает собственный SKU продаваемой карточки."""
        self._change(actor, now, sku=sku)

    def set_virtual(
        self,
        value: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Задаёт собственную виртуальность продаваемой позиции."""
        self._change(actor, now, virtual=value)

    def set_price(
        self,
        value: PriceSpecificationVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет собственную цену без наследования."""
        self._change(actor, now, price=value)

    def set_stock(
        self,
        value: StockSpecificationVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет настройки наличия товара."""
        self._change(actor, now, stock=value)

    def set_measurements(
        self,
        weight: WeightVO | None,
        dimensions: DimensionsVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет собственные измерения вместе с единицами."""
        self._change(actor, now, weight=weight, dimensions=dimensions)

    def put_content(
        self,
        locale: LocaleVO,
        values: dict[str, str],
        schema: ProductTypeSchemaSnapshot,
        expected_schema_version: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет перевод после проверки фиксированной версии схемы."""
        if (
            schema.id != self.product_type_id
            or schema.code != "default"
            or schema.schema_version != expected_schema_version
        ):
            raise CatalogConflictError("Версия схемы изменилась.")
        translations = dict(self.translations)
        translations[locale.value] = dict(values)
        self._change(actor, now, translations=translations)

    def delete_content(
        self,
        locale: LocaleVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Удаляет перевод выбранной locale."""
        translations = dict(self.translations)
        translations.pop(locale.value, None)
        self._change(actor, now, translations=translations)

    def set_attributes(
        self,
        values: tuple[EnumAttributeAssignmentVO, ...],
        definitions: tuple[EnumAttributeSnapshot, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет характеристики после проверки option ID."""
        allowed = {d.id: d.option_ids for d in definitions}
        if any(
            a.attribute_id not in allowed
            or not set(a.option_ids).issubset(allowed[a.attribute_id])
            for a in values
        ):
            raise InvalidCatalogValueError("Option отсутствует в определении.")
        self._change(
            actor,
            now,
            attributes=tuple(sorted(values, key=lambda a: a.position)),
        )

    def set_categories(
        self,
        ids: tuple[EntityIdVO, ...],
        primary: EntityIdVO | None,
        existing: frozenset[EntityIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает категории товара и ровно одну основную непустого набора."""
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Категория отсутствует в tenant.")
        self._change(actor, now, category_ids=ids, primary_category_id=primary)

    def set_tags(
        self,
        ids: tuple[EntityIdVO, ...],
        existing: frozenset[EntityIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает уникальные метки товару."""
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Метка отсутствует в tenant.")
        self._change(actor, now, tag_ids=ids)

    def set_metadata(
        self,
        values: tuple[CatalogMetadataEntry, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет полный набор канонических ключей."""
        self._change(
            actor,
            now,
            metadata=tuple(sorted(values, key=lambda m: m.position)),
        )

    def replace_gallery(
        self,
        locale: LocaleVO,
        gallery: CatalogItemGallery,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Задаёт полный набор изображений выбранной locale."""
        galleries = dict(self.galleries)
        galleries[locale.value] = gallery
        self._change(actor, now, galleries=galleries)

    def delete_gallery(
        self,
        locale: LocaleVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Снимает локализованную галерею."""
        galleries = dict(self.galleries)
        galleries.pop(locale.value, None)
        self._change(actor, now, galleries=galleries)

    def set_primary_image(
        self,
        locale: LocaleVO,
        image_id: EntityIdVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет главное только в явно созданной собственной галерее."""
        gallery = self.galleries.get(locale.value)
        if gallery is None:
            raise InvalidCatalogValueError("Сначала явно создайте собственную галерею.")
        self.replace_gallery(
            locale,
            CatalogItemGallery.create(gallery.images, image_id),
            actor,
            now,
        )

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
        self.replace_gallery(
            locale,
            CatalogItemGallery.create((*images, added), primary),
            actor,
            now,
        )
