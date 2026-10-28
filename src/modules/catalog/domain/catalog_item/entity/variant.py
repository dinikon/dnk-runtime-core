from dataclasses import dataclass, field, replace
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
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
    WeightVO,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.policy.validation import validate_gallery
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class CatalogVariant:
    """Принадлежащая карточке продаваемая позиция с собственными переопределениями."""

    id: CatalogItemIdVO
    parent_id: CatalogItemIdVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    status: CatalogItemStatus = CatalogItemStatus.DRAFT
    sku: SkuCodeVO | None = None
    virtual: bool = False
    price: PriceSpecificationVO | None = None
    stock: StockSpecificationVO = field(default_factory=StockSpecificationVO)
    weight: WeightVO | None = None
    dimensions: DimensionsVO | None = None
    translations: dict[str, dict[str, str]] = field(default_factory=dict)
    galleries: dict[str, CatalogItemGallery] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        identifier: CatalogItemIdVO,
        parent_id: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> "CatalogVariant":
        """Создаёт Draft с ручным наличием и наследованием контента и изображений."""
        return cls.restore(
            identifier=identifier,
            parent_id=parent_id,
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
        parent_id: CatalogItemIdVO,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        status: CatalogItemStatus = CatalogItemStatus.DRAFT,
        sku: SkuCodeVO | None = None,
        virtual: bool = False,
        price: PriceSpecificationVO | None = None,
        stock: StockSpecificationVO = StockSpecificationVO(),
        weight: WeightVO | None = None,
        dimensions: DimensionsVO | None = None,
        translations: dict[str, dict[str, str]] | None = None,
        galleries: dict[str, CatalogItemGallery] | None = None,
    ) -> "CatalogVariant":
        """Восстанавливает собственные значения без материализации наследования."""
        item = cls(
            identifier,
            parent_id,
            created_at,
            updated_at,
            created_by,
            updated_by,
            status,
            sku,
            virtual,
            price,
            stock,
            weight,
            dimensions,
            {k: dict(v) for k, v in (translations or {}).items()},
            dict(galleries or {}),
        )
        item.validate()
        return item

    def validate(self) -> None:
        """Проверяет идентичность, типы и частичные локализованные переопределения."""
        if (
            not isinstance(self.id, CatalogItemIdVO)
            or not isinstance(self.parent_id, CatalogItemIdVO)
            or self.id == self.parent_id
        ):
            raise InvalidCatalogValueError("Некорректная идентичность варианта.")
        if (
            not isinstance(self.status, CatalogItemStatus)
            or type(self.virtual) is not bool
        ):
            raise InvalidCatalogValueError("Некорректный статус или источник остатка.")
        if (
            not isinstance(self.created_by, EntityIdVO)
            or not isinstance(self.updated_by, EntityIdVO)
            or any(
                v.tzinfo is None or v.utcoffset() is None
                for v in (self.created_at, self.updated_at)
            )
        ):
            raise InvalidCatalogValueError("Некорректный audit варианта.")
        for value, expected, name in (
            (self.sku, SkuCodeVO, "sku"),
            (self.price, PriceSpecificationVO, "price_specification"),
            (self.weight, WeightVO, "weight"),
            (self.dimensions, DimensionsVO, "dimensions"),
        ):
            if value is not None and not isinstance(value, expected):
                raise InvalidCatalogValueError(
                    "Некорректное значение варианта.", (name,)
                )
        if not isinstance(self.stock, StockSpecificationVO):
            raise InvalidCatalogValueError(
                "Нужны собственные настройки остатка.", ("stock",)
            )
        for locale, values in self.translations.items():
            LocaleVO(locale)
            if any(not isinstance(v, str) or len(v) > 1000000 for v in values.values()):
                raise InvalidCatalogValueError("Контент требует текст.", ("content",))
            if "title" in values and (
                not values["title"].strip() or len(values["title"]) > 255
            ):
                raise InvalidCatalogValueError(
                    "Собственное название не может быть пустым.", ("content",)
                )
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            validate_gallery(gallery)
        image_ids = [i.id for g in self.galleries.values() for i in g.images]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений варианта должны быть уникальны."
            )

    def snapshot(self, product_type_id: EntityIdVO) -> CatalogItemValuesSnapshot:
        """Возвращает собственные значения для чистой политики и persistence."""
        return CatalogItemValuesSnapshot(
            id=self.id,
            product_type_id=product_type_id,
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
            kind=CatalogItemKind.VARIANT,
            parent_id=self.parent_id,
        )

    def changed(
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
    ) -> "CatalogVariant":
        """Готовит кандидата; агрегат проверяет наследование перед применением."""
        values = {
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
            "price" if k == "price_specification" else k: v
            for k, v in values.items()
            if k in fields
        }
        if (
            "dimensions" in fields
            and dimensions is not None
            and all(
                value is None
                for value in (dimensions.length, dimensions.width, dimensions.height)
            )
        ):
            changes["dimensions"] = None
        if fields & {"content", "gallery"}:
            if locale is None:
                raise InvalidCatalogValueError("Укажите locale.")
            if "content" in fields:
                translations = {k: dict(v) for k, v in self.translations.items()}
                if content is None:
                    translations.pop(locale.value, None)
                else:
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
        candidate.validate()
        return (
            replace(candidate, updated_at=now, updated_by=actor)
            if candidate != self
            else self
        )
