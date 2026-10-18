from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Self
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
        )
        item._validate()
        if item.translations:
            if schema is None or schema.id != product_type_id:
                raise InvalidCatalogValueError(
                    "Для восстановления контента нужна схема товара."
                )
            for values in item.translations.values():
                schema.validate_content(values)
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
        for locale, values in self.translations.items():
            LocaleVO(locale)
            self._validate_content(values)
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            self._validate_gallery(gallery)
        image_ids = [
            image.id for gallery in self.galleries.values() for image in gallery.images
        ]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений уникальны во всех locale товара."
            )

    @staticmethod
    def _validate_content(values: dict[str, str]) -> None:
        """Проверяет форму сохранённых текстовых значений и каноническое имя товара."""
        if any(
            (
                not isinstance(value, str) or len(value) > 1000000
                for value in values.values()
            )
        ):
            raise InvalidCatalogValueError(
                "Контент требует текст до 1000000 символов.", ("content",)
            )
        if (
            "title" not in values
            or not values["title"].strip()
            or len(values["title"]) > 255
        ):
            raise InvalidCatalogValueError(
                "Title должен быть непустым текстом до 255 символов.", ("content",)
            )

    @staticmethod
    def _validate_gallery(gallery: CatalogItemGallery) -> None:
        """Проверяет идентичности, порядок и главное изображение всего набора."""
        images = gallery.images
        if (
            len(images) > 100
            or len({i.id for i in images}) != len(images)
            or len({i.file_id for i in images}) != len(images)
            or (len({i.position for i in images}) != len(images))
            or any(
                (
                    type(i.position) is not int
                    or i.position < 0
                    or not isinstance(i.id, EntityIdVO)
                    or not isinstance(i.file_id, EntityIdVO)
                    or (len(i.alt) > 1000)
                    or (len(i.caption) > 5000)
                    for i in images
                )
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
