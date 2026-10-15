from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Self
import re
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideVO,
    OverrideMode,
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
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.policy.effective_values import (
    CatalogItemEffectiveValuesPolicy,
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
    CatalogNotFoundError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class CatalogItem:
    """Корень SIMPLE/VARIABLE или принадлежащий ему узел VARIANT той же модели."""

    id: CatalogItemIdVO
    kind: CatalogItemKind
    parent_id: CatalogItemIdVO | None
    product_type_id: EntityIdVO | None
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
    translations: dict[str, dict[str, OverrideVO[str]]] = field(default_factory=dict)
    galleries: dict[str, CatalogItemGallery] = field(default_factory=dict)
    attributes: tuple[EnumAttributeAssignmentVO, ...] = ()
    metadata: tuple[CatalogMetadataEntry, ...] = ()
    axes: tuple[VariationAxis, ...] = ()
    default_selection: VariationSelectionVO | None = None
    selection: VariationSelectionVO = VariationSelectionVO()
    category_ids: tuple[EntityIdVO, ...] = ()
    primary_category_id: EntityIdVO | None = None
    tag_ids: tuple[EntityIdVO, ...] = ()
    children: tuple["CatalogItem", ...] = ()

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
            kind=CatalogItemKind.SIMPLE,
            parent_id=None,
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
    def create_variant(
        cls,
        identifier: CatalogItemIdVO,
        parent_id: CatalogItemIdVO,
        selection: VariationSelectionVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт дочерний узел для проверки в составе VARIABLE."""
        return cls.restore(
            identifier=identifier,
            kind=CatalogItemKind.VARIANT,
            parent_id=parent_id,
            product_type_id=None,
            status=CatalogItemStatus.DRAFT,
            sku=None,
            virtual=False,
            price=None,
            weight=None,
            dimensions=None,
            stock=StockSpecificationVO(),
            revision=1,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
            selection=selection,
        )

    @classmethod
    def create_variable(
        cls,
        identifier: CatalogItemIdVO,
        axes: tuple[VariationAxis, ...],
        children: tuple["CatalogItem", ...],
        default_selection: VariationSelectionVO | None,
        definitions: tuple[EnumAttributeSnapshot, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт семью после проверки осей и полного набора детей."""
        root = cls.create_simple(identifier, actor, now)
        candidate = replace(
            root,
            kind=CatalogItemKind.VARIABLE,
            axes=axes,
            children=children,
            default_selection=default_selection,
        )
        candidate._validate(definitions)
        return candidate

    @classmethod
    def restore(
        cls,
        *,
        identifier: CatalogItemIdVO,
        kind: CatalogItemKind,
        parent_id: CatalogItemIdVO | None,
        product_type_id: EntityIdVO | None,
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
        translations: dict[str, dict[str, OverrideVO[str]]] | None = None,
        galleries: dict[str, CatalogItemGallery] | None = None,
        attributes: tuple[EnumAttributeAssignmentVO, ...] = (),
        metadata: tuple[CatalogMetadataEntry, ...] = (),
        axes: tuple[VariationAxis, ...] = (),
        default_selection: VariationSelectionVO | None = None,
        selection: VariationSelectionVO = VariationSelectionVO(),
        category_ids: tuple[EntityIdVO, ...] = (),
        primary_category_id: EntityIdVO | None = None,
        tag_ids: tuple[EntityIdVO, ...] = (),
        children: tuple["CatalogItem", ...] = (),
    ) -> Self:
        """Восстанавливает собственные значения; mapper не исправляет инварианты."""
        item = cls(
            identifier,
            kind,
            parent_id,
            product_type_id,
            status,
            sku,
            virtual,
            price,
            weight,
            dimensions,
            stock,
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
            {k: dict(v) for k, v in (translations or {}).items()},
            dict(galleries or {}),
            attributes,
            metadata,
            axes,
            default_selection,
            selection,
            category_ids,
            primary_category_id,
            tag_ids,
            children,
        )
        item._validate()
        return item

    def snapshot(self) -> CatalogItemValuesSnapshot:
        """Передаёт собственные значения чистой политике без ссылки на агрегат."""
        return CatalogItemValuesSnapshot(
            self.id,
            self.kind,
            self.parent_id,
            self.product_type_id,
            self.status,
            self.sku.value if self.sku else None,
            self.virtual,
            self.price,
            self.weight,
            self.dimensions,
            self.stock,
            {k: dict(v) for k, v in self.translations.items()},
            dict(self.galleries),
            self.attributes,
            self.metadata,
            self.selection,
            self.axes,
            self.default_selection,
            self.category_ids,
            self.primary_category_id,
            self.tag_ids,
            self.revision,
            self.created_at,
            self.updated_at,
            self.created_by,
            self.updated_by,
        )

    def find_item(self, identifier: CatalogItemIdVO) -> "CatalogItem":
        """Разрешает идентичность только в границе текущего корня."""
        if self.id == identifier:
            return self
        for child in self.children:
            if child.id == identifier:
                return child
        raise CatalogNotFoundError("CatalogItem не принадлежит семье.")

    def prepare_variant(
        self,
        identifier: CatalogItemIdVO,
        selection: VariationSelectionVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> "CatalogItem":
        """Создаёт кандидат существующего ребёнка для атомарной замены структуры."""
        previous = self.find_item(identifier)
        if previous.kind != CatalogItemKind.VARIANT:
            raise InvalidCatalogValueError(
                "Существующий ID должен принадлежать дочернему варианту."
            )
        if previous.selection == selection:
            return previous
        candidate = replace(
            previous,
            selection=selection,
            revision=previous.revision + 1,
            updated_at=now,
            updated_by=actor,
        )
        candidate._validate()
        return candidate

    def ensure_revision(self, expected: int) -> None:
        """Отклоняет запись по устаревшей ревизии семьи."""
        if type(expected) is not int or expected != self.revision:
            raise CatalogConflictError(
                "Ревизия семьи изменилась. Загрузите актуальные данные."
            )

    def ensure_deletable(
        self, used: bool, discarded_ids: frozenset[CatalogItemIdVO] = frozenset()
    ) -> None:
        """Запрещает удаление семьи с внешними зависимостями."""
        if discarded_ids != frozenset(c.id for c in self.children):
            raise InvalidCatalogValueError(
                "Удаление требует явные ID всех дочерних вариантов."
            )
        if self.kind == CatalogItemKind.VARIANT or used:
            raise CatalogConflictError(
                "Удаление требует корень без внешних зависимостей."
            )

    def _validate(
        self, definitions: tuple[EnumAttributeSnapshot, ...] | None = None
    ) -> None:
        """Проверяет итоговые инварианты узла и принадлежащей структуры."""
        if (
            not isinstance(self.id, CatalogItemIdVO)
            or not isinstance(self.created_by, EntityIdVO)
            or not isinstance(self.updated_by, EntityIdVO)
            or (
                self.parent_id is not None
                and not isinstance(self.parent_id, CatalogItemIdVO)
            )
            or not isinstance(self.kind, CatalogItemKind)
            or not isinstance(self.status, CatalogItemStatus)
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность, kind, status или revision."
            )
        if any(
            v.tzinfo is None or v.utcoffset() is None
            for v in (self.created_at, self.updated_at)
        ):
            raise InvalidCatalogValueError("Audit требует timezone.")
        if self.kind == CatalogItemKind.VARIANT:
            if (
                self.parent_id is None
                or self.parent_id == self.id
                or self.product_type_id is not None
                or self.children
                or self.axes
                or self.default_selection is not None
            ):
                raise InvalidCatalogValueError(
                    "VARIANT требует родителя и не имеет собственной семьи/схемы."
                )
        elif (
            self.parent_id is not None
            or self.product_type_id != DEFAULT_TYPE_ID
            or self.selection.values
        ):
            raise InvalidCatalogValueError(
                "Корень использует Default и не имеет родителя/selection."
            )
        if self.kind != CatalogItemKind.VARIABLE and (
            self.children or self.axes or self.default_selection is not None
        ):
            raise InvalidCatalogValueError("Только VARIABLE имеет оси и детей.")
        if self.kind != CatalogItemKind.SIMPLE and (
            self.category_ids or self.tag_ids or self.primary_category_id is not None
        ):
            raise InvalidCatalogValueError(
                "Категории и теги назначаются только SIMPLE."
            )
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
        if self.kind == CatalogItemKind.VARIABLE and self.sku is not None:
            raise InvalidCatalogValueError("SKU принадлежит продаваемой позиции.")
        if type(self.virtual) is not bool:
            raise InvalidCatalogValueError("Virtual требует bool.")
        if self.kind == CatalogItemKind.VARIABLE and (
            self.virtual or self.price is not None
        ):
            raise InvalidCatalogValueError(
                "VARIABLE не имеет собственной цены и virtual=true."
            )
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
            self._validate_content(values, self.kind == CatalogItemKind.VARIANT)
        for locale, gallery in self.galleries.items():
            LocaleVO(locale)
            self._validate_gallery(gallery)
        if len({a.attribute_id for a in self.attributes}) != len(
            self.attributes
        ) or len({a.position for a in self.attributes}) != len(self.attributes):
            raise InvalidCatalogValueError("Атрибуты и позиции назначений уникальны.")
        image_ids = [
            image.id
            for item in (self, *self.children)
            for gallery in item.galleries.values()
            for image in gallery.images
        ]
        if len(set(image_ids)) != len(image_ids):
            raise InvalidCatalogValueError(
                "ID изображений уникальны во всей семье и её locale."
            )
        self._validate_metadata(self.metadata)
        if definitions is not None:
            allowed = {d.id: d.option_ids for d in definitions}
            if any(
                not set(a.option_ids).issubset(allowed.get(a.attribute_id, frozenset()))
                or a.attribute_id not in allowed
                for a in self.attributes
            ):
                raise InvalidCatalogValueError("Options не принадлежат определению.")
        if self.kind == CatalogItemKind.VARIABLE:
            if (
                not self.axes
                or len(self.children) < 2
                or len({a.attribute_id for a in self.axes}) != len(self.axes)
                or len({a.position for a in self.axes}) != len(self.axes)
                or len({c.id for c in self.children}) != len(self.children)
            ):
                raise InvalidCatalogValueError(
                    "VARIABLE требует уникальные оси и минимум два ребёнка."
                )
            if any(
                a.attribute_id in {axis.attribute_id for axis in self.axes}
                for a in self.attributes
            ):
                raise InvalidCatalogValueError(
                    "Ось уже представляет атрибут родителя; второе назначение недопустимо."
                )
            allowed = {a.attribute_id: set(a.option_ids) for a in self.axes}
            if definitions is not None and any(
                a not in {d.id for d in definitions}
                or not opts.issubset(
                    next(d.option_ids for d in definitions if d.id == a)
                )
                for a, opts in allowed.items()
            ):
                raise InvalidCatalogValueError("Ось использует чужие options.")
            combinations = set()
            currencies = set()
            skus = set()
            parent = self.snapshot()
            for child in self.children:
                child._validate()
                if (
                    child.kind != CatalogItemKind.VARIANT
                    or child.parent_id != self.id
                    or child.id == self.id
                ):
                    raise InvalidCatalogValueError(
                        "Ребёнок должен быть VARIANT этого VARIABLE."
                    )
                selected = dict(child.selection.values)
                if (
                    set(selected) != set(allowed)
                    or any(o not in allowed[a] for a, o in selected.items())
                    or child.selection in combinations
                ):
                    raise InvalidCatalogValueError(
                        "Комбинации полные, допустимые и уникальные."
                    )
                if any(a.attribute_id in allowed for a in child.attributes):
                    raise InvalidCatalogValueError(
                        "Осевой атрибут варианта задаётся только selection."
                    )
                combinations.add(child.selection)
                effective = CatalogItemEffectiveValuesPolicy.resolve(
                    child.snapshot(), parent, "en", self.updated_at
                )
                if effective.price_specification:
                    currencies.add(effective.price_specification.currency)
                if child.sku:
                    if child.sku.value in skus:
                        raise InvalidCatalogValueError(
                            "SKU детей должны быть уникальны."
                        )
                    skus.add(child.sku.value)
            if len(currencies) > 1:
                raise InvalidCatalogValueError("Семья использует одну валюту.")
            if (
                self.default_selection is not None
                and self.default_selection not in combinations
            ):
                raise InvalidCatalogValueError(
                    "Default должен совпадать с существующей комбинацией."
                )

    @staticmethod
    def _validate_content(values: dict[str, OverrideVO[str]], variant: bool) -> None:
        """Проверяет фиксированные блоки и обязательность собственного имени корня."""
        if set(values) - {"name", "desc", "short_desc"}:
            raise InvalidCatalogValueError("Блок отсутствует в Default.")
        for code, value in values.items():
            if value.mode == OverrideMode.INHERIT or (
                value.mode == OverrideMode.SET
                and (not isinstance(value.value, str) or len(value.value) > 1_000_000)
            ):
                raise InvalidCatalogValueError(
                    "Контент принимает set/clear текста; отсутствие ключа означает inherit."
                )
            if code == "name" and (
                value.mode != OverrideMode.SET
                or not value.value.strip()
                or len(value.value) > 255
            ):
                raise InvalidCatalogValueError(
                    "Name должен быть непустым текстом до 255 символов."
                )
        if not variant and (
            "name" not in values or values["name"].mode != OverrideMode.SET
        ):
            raise InvalidCatalogValueError("Own-перевод корня требует name.")

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
            if v.mode == OverrideMode.CLEAR:
                if v.value is not None or v.value_type is not None:
                    raise InvalidCatalogValueError("Clear не содержит значения.")
            elif v.mode != OverrideMode.SET or not (
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

    def _replace_item(
        self,
        item_id: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
        **changes: object,
    ) -> None:
        """Проверяет кандидат до атомарного принятия состояния и ревизий семьи."""
        if self.kind == CatalogItemKind.VARIANT:
            raise InvalidCatalogValueError("Изменение проходит через корень семьи.")
        before = self.find_item(item_id)
        updated = replace(
            before,
            **changes,
            revision=before.revision + 1,
            updated_by=actor,
            updated_at=now,
        )
        if before is self:
            candidate = updated
        else:
            candidate = replace(
                self,
                children=tuple(
                    updated if c.id == item_id else c for c in self.children
                ),
                revision=self.revision + 1,
                updated_by=actor,
                updated_at=now,
            )
        candidate._validate()
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(candidate, name))

    def set_status(
        self,
        item_id: CatalogItemIdVO,
        status: CatalogItemStatus,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет локальный статус, не переписывая статусы детей."""
        self._replace_item(item_id, actor, now, status=status)

    def set_sku(
        self,
        item_id: CatalogItemIdVO,
        sku: SkuCodeVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает собственный SKU продаваемой карточки."""
        self._replace_item(item_id, actor, now, sku=sku)

    def set_virtual(
        self,
        item_id: CatalogItemIdVO,
        value: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Задаёт собственную виртуальность продаваемой позиции."""
        if self.find_item(item_id).kind == CatalogItemKind.VARIABLE:
            raise InvalidCatalogValueError("Virtual задаётся только SIMPLE/VARIANT.")
        self._replace_item(item_id, actor, now, virtual=value)

    def set_price(
        self,
        item_id: CatalogItemIdVO,
        value: PriceSpecificationVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет собственную цену и проверяет единую валюту семьи."""
        if self.find_item(item_id).kind == CatalogItemKind.VARIABLE:
            raise InvalidCatalogValueError("Цена задаётся только SIMPLE/VARIANT.")
        self._replace_item(item_id, actor, now, price=value)

    def set_stock(
        self,
        item_id: CatalogItemIdVO,
        value: StockSpecificationVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет источник наличия и проверяет всех наследующих детей."""
        self._replace_item(item_id, actor, now, stock=value)

    def set_measurements(
        self,
        item_id: CatalogItemIdVO,
        weight: WeightVO | None,
        dimensions: DimensionsVO | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет собственные измерения вместе с единицами."""
        self._replace_item(item_id, actor, now, weight=weight, dimensions=dimensions)

    def put_content(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        values: dict[str, OverrideVO[str]],
        schema: ProductTypeSchemaSnapshot,
        expected_schema_version: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет own-перевод после проверки фиксированной версии схемы."""
        if (
            schema.id != self.product_type_id
            or schema.code != "default"
            or schema.schema_version != expected_schema_version
        ):
            raise CatalogConflictError("Версия схемы изменилась.")
        translations = dict(self.find_item(item_id).translations)
        translations[locale.value] = dict(values)
        self._replace_item(item_id, actor, now, translations=translations)

    def delete_content(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Удаляет own-перевод; ребёнок возвращается к наследованию той же locale."""
        translations = dict(self.find_item(item_id).translations)
        translations.pop(locale.value, None)
        self._replace_item(item_id, actor, now, translations=translations)

    def set_attributes(
        self,
        item_id: CatalogItemIdVO,
        values: tuple[EnumAttributeAssignmentVO, ...],
        definitions: tuple[EnumAttributeSnapshot, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет неосевые характеристики после проверки option ID."""
        allowed = {d.id: d.option_ids for d in definitions}
        if any(
            a.attribute_id not in allowed
            or not set(a.option_ids).issubset(allowed[a.attribute_id])
            for a in values
        ):
            raise InvalidCatalogValueError("Option отсутствует в определении.")
        self._replace_item(
            item_id,
            actor,
            now,
            attributes=tuple(sorted(values, key=lambda a: a.position)),
        )

    def set_categories(
        self,
        item_id: CatalogItemIdVO,
        ids: tuple[EntityIdVO, ...],
        primary: EntityIdVO | None,
        existing: frozenset[EntityIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает категории SIMPLE и ровно одну основную непустого набора."""
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Категория отсутствует в tenant.")
        self._replace_item(
            item_id, actor, now, category_ids=ids, primary_category_id=primary
        )

    def set_tags(
        self,
        item_id: CatalogItemIdVO,
        ids: tuple[EntityIdVO, ...],
        existing: frozenset[EntityIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает уникальные метки только SIMPLE."""
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Метка отсутствует в tenant.")
        self._replace_item(item_id, actor, now, tag_ids=ids)

    def set_metadata(
        self,
        item_id: CatalogItemIdVO,
        values: tuple[CatalogMetadataEntry, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет полный own-набор канонических ключей."""
        self._replace_item(
            item_id,
            actor,
            now,
            metadata=tuple(sorted(values, key=lambda m: m.position)),
        )

    def replace_gallery(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        gallery: CatalogItemGallery,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Задаёт полный own-набор изображений выбранной locale."""
        galleries = dict(self.find_item(item_id).galleries)
        galleries[locale.value] = gallery
        self._replace_item(item_id, actor, now, galleries=galleries)

    def delete_gallery(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Снимает own-галерею и возвращает ребёнка к наследованию."""
        galleries = dict(self.find_item(item_id).galleries)
        galleries.pop(locale.value, None)
        self._replace_item(item_id, actor, now, galleries=galleries)

    def set_primary_image(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        image_id: EntityIdVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет главное только в явно созданной собственной галерее."""
        gallery = self.find_item(item_id).galleries.get(locale.value)
        if gallery is None:
            raise InvalidCatalogValueError("Сначала явно создайте собственную галерею.")
        self.replace_gallery(
            item_id,
            locale,
            CatalogItemGallery.create(gallery.images, image_id),
            actor,
            now,
        )

    def ensure_can_add_image(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        image: CatalogItemImage,
        main: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Проверяет добавление на отдельном кандидате до внешнего Files upload."""
        candidate = replace(self)
        candidate.add_image(item_id, locale, image, main, actor, now)

    def add_image(
        self,
        item_id: CatalogItemIdVO,
        locale: LocaleVO,
        image: CatalogItemImage,
        main: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Добавляет изображение в own-набор, выбирая первое или явно главное."""
        node = self.find_item(item_id)
        gallery = node.galleries.get(locale.value)
        if (
            gallery is None
            and node.kind == CatalogItemKind.VARIANT
            and locale.value in self.galleries
        ):
            raise InvalidCatalogValueError(
                "Для унаследованной галереи сначала задайте собственный набор."
            )
        images = gallery.images if gallery else ()
        added = replace(
            image, position=max((i.position for i in images), default=-1) + 1
        )
        primary = image.id if main or not images else gallery.primary_image_id
        self.replace_gallery(
            item_id,
            locale,
            CatalogItemGallery.create((*images, added), primary),
            actor,
            now,
        )

    def replace_structure(
        self,
        axes: tuple[VariationAxis, ...],
        children: tuple["CatalogItem", ...],
        default: VariationSelectionVO | None,
        definitions: tuple[EnumAttributeSnapshot, ...],
        removed_ids: frozenset[CatalogItemIdVO],
        used_ids: frozenset[CatalogItemIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Принимает полную структуру с явным перечнем удаляемых детей."""
        if self.kind != CatalogItemKind.VARIABLE:
            raise InvalidCatalogValueError("Структура меняется у VARIABLE.")
        removed = {c.id for c in self.children} - {c.id for c in children}
        if removed != set(removed_ids) or removed & set(used_ids):
            raise CatalogConflictError(
                "Удаления требуют точного списка и отсутствия внешних зависимостей."
            )
        candidate = replace(
            self, axes=axes, children=children, default_selection=default
        )
        candidate._validate(definitions)
        self._replace_item(
            self.id, actor, now, axes=axes, children=children, default_selection=default
        )

    def change_to_variable(
        self,
        axes: tuple[VariationAxis, ...],
        children: tuple["CatalogItem", ...],
        default: VariationSelectionVO | None,
        definitions: tuple[EnumAttributeSnapshot, ...],
        carry_to_id: CatalogItemIdVO | None,
        used: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Сохраняет ID корня и явно переносит продаваемые данные в выбранного ребёнка."""
        if (
            self.kind != CatalogItemKind.SIMPLE
            or self.category_ids
            or self.tag_ids
            or used
        ):
            raise CatalogConflictError(
                "Переход требует SIMPLE без классификации и внешних зависимостей."
            )
        if carry_to_id is None:
            raise InvalidCatalogValueError(
                "Переход требует явно выбранного получателя коммерческих значений."
            )
        if carry_to_id is not None:
            if carry_to_id not in {c.id for c in children}:
                raise InvalidCatalogValueError("Получатель не входит в новую семью.")
            children = tuple(
                (
                    replace(
                        c,
                        sku=self.sku,
                        price=self.price,
                        stock=self.stock,
                        virtual=self.virtual,
                    )
                    if c.id == carry_to_id
                    else c
                )
                for c in children
            )
        candidate = replace(
            self,
            kind=CatalogItemKind.VARIABLE,
            sku=None,
            price=None,
            virtual=False,
            stock=StockSpecificationVO(),
            axes=axes,
            children=children,
            default_selection=default,
        )
        candidate._validate(definitions)
        self._replace_item(
            self.id,
            actor,
            now,
            kind=CatalogItemKind.VARIABLE,
            sku=None,
            price=None,
            virtual=False,
            stock=StockSpecificationVO(),
            axes=axes,
            children=children,
            default_selection=default,
        )

    def change_to_simple(
        self,
        selected_id: CatalogItemIdVO,
        discarded_ids: frozenset[CatalogItemIdVO],
        used: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Материализует effective выбранного ребёнка с сохранением ID корня."""
        if (
            self.kind != CatalogItemKind.VARIABLE
            or used
            or discarded_ids != {c.id for c in self.children}
        ):
            raise CatalogConflictError(
                "Переход требует явного удаления всех child ID без внешних связей."
            )
        selected = self.find_item(selected_id)
        if selected is self:
            raise InvalidCatalogValueError("Выберите ребёнка.")
        parent = self.snapshot()
        effective = CatalogItemEffectiveValuesPolicy.resolve(
            selected.snapshot(), parent, "en", now
        )
        translations = {}
        for locale in set(self.translations) | set(selected.translations):
            content = CatalogItemEffectiveValuesPolicy.resolve(
                selected.snapshot(), parent, locale, now
            ).content
            if content:
                translations[locale] = {
                    k: OverrideVO(OverrideMode.SET, v) for k, v in content.items()
                }
        galleries = {
            locale: CatalogItemEffectiveValuesPolicy.resolve(
                selected.snapshot(), parent, locale, now
            ).gallery
            for locale in set(self.galleries) | set(selected.galleries)
        }
        self._replace_item(
            self.id,
            actor,
            now,
            kind=CatalogItemKind.SIMPLE,
            sku=selected.sku,
            status=selected.status,
            virtual=effective.virtual,
            price=effective.price_specification,
            weight=effective.weight,
            dimensions=effective.dimensions,
            stock=effective.stock,
            translations=translations,
            galleries=galleries,
            attributes=tuple(
                replace(value, position=index)
                for index, value in enumerate(effective.attributes)
            ),
            metadata=tuple(
                replace(v, position=i) for i, v in enumerate(effective.metadata)
            ),
            axes=(),
            children=(),
            default_selection=None,
        )
