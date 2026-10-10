from src.modules.catalog.domain.product.value_object.attribute_value import (
    ProductAttributeValueVO,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.product.value_object.schema import ProductSchemaSnapshot
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.entity.structure import (
    SimpleProductStructure,
    VariableProductStructure,
)
from src.modules.catalog.domain.product.policy.content import ProductContentPolicy
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.product.error import VariantNotFoundError
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


class ProductKind(StrEnum):
    """Фиксированные бизнес-структуры канонического товара."""

    SIMPLE = "simple"
    VARIABLE = "variable"


@dataclass(slots=True)
class Product:
    """Корень товара; защищает структуру, позиции и локализованный контент."""

    id: ProductIdVO
    kind: ProductKind
    product_type_id: ProductTypeIdVO
    structure: SimpleProductStructure | VariableProductStructure
    translations: dict[str, dict[str, str]]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    attribute_values: tuple[ProductAttributeValueVO, ...] = ()
    category_ids: tuple[CategoryIdVO, ...] = ()
    primary_category_id: CategoryIdVO | None = None
    tag_ids: tuple[TagIdVO, ...] = ()

    @classmethod
    def create(
        cls,
        identifier: ProductIdVO,
        schema: ProductSchemaSnapshot,
        variant_id: VariantIdVO,
        virtual: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт SIMPLE с одной позицией без обязательного перевода."""
        return cls.restore(
            identifier=identifier,
            kind=ProductKind.SIMPLE,
            product_type_id=schema.product_type_id,
            structure=SimpleProductStructure.create(
                Variant.create(variant_id, virtual)
            ),
            translations={},
            revision=1,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def create_variable(
        cls,
        identifier: ProductIdVO,
        schema: ProductSchemaSnapshot,
        structure: VariableProductStructure,
        definitions: tuple[EnumAttributeSnapshot, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт VARIABLE после проверки осей и полного набора позиций."""
        cls._validate_structure(ProductKind.VARIABLE, structure, definitions)
        return cls.restore(
            identifier=identifier,
            kind=ProductKind.VARIABLE,
            product_type_id=schema.product_type_id,
            structure=structure,
            translations={},
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
        identifier: ProductIdVO,
        kind: ProductKind,
        product_type_id: ProductTypeIdVO,
        structure: SimpleProductStructure | VariableProductStructure,
        translations: dict[str, dict[str, str]],
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        attribute_values: tuple[ProductAttributeValueVO, ...] = (),
        category_ids: tuple[CategoryIdVO, ...] = (),
        primary_category_id: CategoryIdVO | None = None,
        tag_ids: tuple[TagIdVO, ...] = (),
        primary_category_ids: tuple[CategoryIdVO, ...] | None = None,
    ) -> Self:
        """Восстанавливает агрегат, не исправляя его структуру в mapper."""
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise InvalidCatalogValueError("Некорректная ревизия.")
        cls._validate_structure(kind, structure)
        cls._validate_attribute_values(attribute_values)
        if primary_category_ids is not None:
            if primary_category_id is not None and primary_category_ids != (
                primary_category_id,
            ):
                raise InvalidCatalogValueError("Несогласованная основная категория.")
            if len(primary_category_ids) != int(bool(category_ids)):
                raise InvalidCatalogValueError("Некорректное число основных категорий.")
            primary_category_id = (
                primary_category_ids[0] if primary_category_ids else None
            )
        cls._validate_categories(category_ids, primary_category_id)
        cls._validate_tags(tag_ids)
        for locale in translations:
            LocaleVO(locale)
        return cls(
            identifier,
            kind,
            product_type_id,
            structure,
            {k: dict(v) for k, v in translations.items()},
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
            attribute_values,
            category_ids,
            primary_category_id,
            tag_ids,
        )

    @property
    def variants(self) -> tuple[Variant, ...]:
        """Возвращает позиции выбранной структуры через границу Product."""
        return (
            (self.structure.variant,)
            if isinstance(self.structure, SimpleProductStructure)
            else self.structure.variants
        )

    def find_variant(self, identifier: VariantIdVO) -> Variant:
        """Проверяет принадлежность позиции агрегату по её устойчивому ID."""
        for variant in self.variants:
            if variant.id == identifier:
                return variant
        raise VariantNotFoundError("Позиция отсутствует в Product.")

    @staticmethod
    def _validate_structure(
        kind: ProductKind,
        structure: SimpleProductStructure | VariableProductStructure,
        definitions: tuple[EnumAttributeSnapshot, ...] | None = None,
    ) -> None:
        """Проверяет все инварианты структуры и ссылки по immutable снимкам."""
        if kind == ProductKind.SIMPLE and isinstance(structure, SimpleProductStructure):
            if (
                len(structure.variants) != 1
                or structure.axes
                or structure.default_selection is not None
                or not isinstance(structure.variant, Variant)
                or structure.variant.selection.values
                or structure.variant.translations
            ):
                raise InvalidCatalogValueError(
                    "SIMPLE требует одну позицию без selection и VARIANT-переводов."
                )
            return
        if kind != ProductKind.VARIABLE or not isinstance(
            structure, VariableProductStructure
        ):
            raise InvalidCatalogValueError("Kind и структура Product не согласованы.")
        axes = structure.axes
        if not axes or len(structure.variants) < 2:
            raise InvalidCatalogValueError(
                "VARIABLE требует оси и минимум две позиции."
            )
        if len({a.attribute_id for a in axes}) != len(axes) or len(
            {a.position for a in axes}
        ) != len(axes):
            raise InvalidCatalogValueError(
                "Характеристики и позиции осей должны быть уникальны."
            )
        if any(not isinstance(v, Variant) for v in structure.variants) or len(
            {v.id for v in structure.variants}
        ) != len(structure.variants):
            raise InvalidCatalogValueError("ID позиций должны быть уникальны.")
        allowed = {a.attribute_id: set(a.option_ids) for a in axes}
        if definitions is not None:
            snapshots = {d.id: d.option_ids for d in definitions}
            for identifier, options in allowed.items():
                if identifier not in snapshots or not options.issubset(
                    snapshots[identifier]
                ):
                    raise InvalidCatalogValueError(
                        "Ось содержит option вне определения характеристики."
                    )
        combinations = set()
        for variant in structure.variants:
            selected = dict(variant.selection.values)
            if set(selected) != set(allowed) or any(
                o not in allowed[a] for a, o in selected.items()
            ):
                raise InvalidCatalogValueError(
                    "Комбинация должна полностью соответствовать разрешённым осям."
                )
            if variant.selection in combinations:
                raise InvalidCatalogValueError(
                    "Комбинации вариантов должны быть уникальны."
                )
            combinations.add(variant.selection)
        if (
            structure.default_selection is not None
            and structure.default_selection not in combinations
        ):
            raise InvalidCatalogValueError(
                "Default selection должен соответствовать существующей позиции."
            )

    def replace_variants(
        self,
        structure: VariableProductStructure,
        definitions: tuple[EnumAttributeSnapshot, ...],
        schema: ProductSchemaSnapshot,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет полную структуру VARIABLE с сохранением контента существующих ID."""
        if self.kind != ProductKind.VARIABLE:
            raise InvalidCatalogValueError("Для SIMPLE используйте явный переход вида.")
        self._replace_structure(
            ProductKind.VARIABLE, structure, definitions, schema, actor, now
        )

    def change_kind(
        self,
        kind: ProductKind,
        structure: SimpleProductStructure | VariableProductStructure,
        definitions: tuple[EnumAttributeSnapshot, ...],
        schema: ProductSchemaSnapshot,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Выполняет атомарный переход вида без скрытой потери переводов."""
        if kind == self.kind:
            raise InvalidCatalogValueError("Выберите другой вид товара.")
        self._replace_structure(kind, structure, definitions, schema, actor, now)

    def _replace_structure(
        self,
        kind: ProductKind,
        structure: SimpleProductStructure | VariableProductStructure,
        definitions: tuple[EnumAttributeSnapshot, ...],
        schema: ProductSchemaSnapshot,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Подготавливает и проверяет новое состояние до изменения текущего агрегата."""
        old = {v.id: v for v in self.variants}
        if isinstance(structure, SimpleProductStructure):
            self._validate_structure(kind, structure, definitions)
        incoming = (
            (structure.variant,)
            if isinstance(structure, SimpleProductStructure)
            else structure.variants
        )
        retained = {v.id for v in incoming}
        if any(
            v.translations
            for identifier, v in old.items()
            if identifier not in retained
        ):
            raise CatalogConflictError(
                "Удаляемая позиция имеет переводы. Сначала явно удалите их."
            )
        variants = tuple(
            Variant.restore(
                v.id,
                v.virtual,
                v.downloadable,
                old[v.id].translations if v.id in old else v.translations,
                v.selection,
            )
            for v in incoming
        )
        candidate = (
            SimpleProductStructure.create(variants[0])
            if isinstance(structure, SimpleProductStructure)
            else VariableProductStructure.create(
                structure.axes, structure.default_selection, variants
            )
        )
        self._validate_structure(kind, candidate, definitions)
        self.validate_content(schema)
        for variant in variants:
            for values in variant.translations.values():
                ProductContentPolicy.validate(values, schema, ContentScope.VARIANT)
        self.kind = kind
        self.structure = candidate
        self._touch(actor, now)

    def validate_content(self, schema: ProductSchemaSnapshot) -> None:
        """Проверяет все сохранённые локали товара и каждого варианта."""
        self._validate_structure(self.kind, self.structure)
        for values in self.translations.values():
            ProductContentPolicy.validate(values, schema, ContentScope.PRODUCT)
        for variant in self.variants:
            for values in variant.translations.values():
                ProductContentPolicy.validate(values, schema, ContentScope.VARIANT)

    def change_type(
        self, schema: ProductSchemaSnapshot, actor: EntityIdVO, now: datetime
    ) -> None:
        """Меняет тип после проверки всего контента без скрытой очистки."""
        self.validate_content(schema)
        self.product_type_id = schema.product_type_id
        self._touch(actor, now)

    def put_content(
        self,
        locale: LocaleVO,
        values: dict[str, str],
        schema: ProductSchemaSnapshot,
        scope: ContentScope,
        actor: EntityIdVO,
        now: datetime,
        variant_id: VariantIdVO | None = None,
    ) -> None:
        """Сохраняет перевод товара либо выбранного варианта после доменных проверок."""
        self._ensure_content_scope(scope)
        if schema.product_type_id != self.product_type_id:
            raise CatalogConflictError("Тип контента изменился.")
        ProductContentPolicy.validate(values, schema, scope)
        if scope == ContentScope.PRODUCT:
            self.translations[locale.value] = dict(values)
        else:
            if variant_id is None:
                raise InvalidCatalogValueError("Для VARIANT требуется ID позиции.")
            self.find_variant(variant_id).put_content(locale, values)
        self._touch(actor, now)

    def delete_content(
        self,
        locale: LocaleVO,
        scope: ContentScope,
        actor: EntityIdVO,
        now: datetime,
        variant_id: VariantIdVO | None = None,
    ) -> None:
        """Удаляет ровно один явный перевод, не меняя другой scope или locale."""
        self._ensure_content_scope(scope)
        if scope == ContentScope.PRODUCT:
            self.translations.pop(locale.value, None)
        else:
            if variant_id is None:
                raise InvalidCatalogValueError("Для VARIANT требуется ID позиции.")
            self.find_variant(variant_id).delete_content(locale)
        self._touch(actor, now)

    def _ensure_content_scope(self, scope: ContentScope) -> None:
        """Запрещает активный контент позиции SIMPLE."""
        if self.kind == ProductKind.SIMPLE and scope == ContentScope.VARIANT:
            raise InvalidCatalogValueError(
                "Контент SIMPLE редактируется только у Product."
            )

    def set_variant_properties(
        self,
        variant_id: VariantIdVO,
        virtual: bool,
        downloadable: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет свойства только позиции, принадлежащей этому Product."""
        self.find_variant(variant_id).set_properties(virtual, downloadable)
        self._touch(actor, now)

    def ensure_revision(self, expected: int) -> None:
        """Отклоняет запись из устаревшей ревизии."""
        if expected != self.revision:
            raise CatalogConflictError(
                "Ревизия изменилась. Загрузите актуальное состояние."
            )

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует ревизию и автора доменного изменения."""
        self.revision += 1
        self.updated_by = actor
        self.updated_at = now

    @staticmethod
    def _validate_attribute_values(
        values: tuple[ProductAttributeValueVO, ...],
        definitions: tuple[EnumAttributeSnapshot, ...] | None = None,
    ) -> None:
        """Проверяет уникальность общих значений и принадлежность option определению."""
        if (
            any(not isinstance(v, ProductAttributeValueVO) for v in values)
            or len({v.attribute_id for v in values}) != len(values)
            or len({v.position for v in values}) != len(values)
        ):
            raise InvalidCatalogValueError(
                "Определения и позиции характеристик должны быть уникальны."
            )
        if definitions is not None:
            allowed = {d.id: d.option_ids for d in definitions}
            if any(
                v.option_id not in allowed.get(v.attribute_id, frozenset())
                for v in values
            ):
                raise InvalidCatalogValueError(
                    "Option не принадлежит определению характеристики."
                )

    @staticmethod
    def _validate_categories(
        ids: tuple[CategoryIdVO, ...], primary: CategoryIdVO | None
    ) -> None:
        """Требует явный уникальный набор и одну основную категорию непустого набора."""
        if (
            any(not isinstance(i, CategoryIdVO) for i in ids)
            or len(set(ids)) != len(ids)
            or (bool(ids) and primary not in ids)
            or (not ids and primary is not None)
        ):
            raise InvalidCatalogValueError(
                "Назначьте одну основную категорию из уникального непустого набора."
            )

    @staticmethod
    def _validate_tags(ids: tuple[TagIdVO, ...]) -> None:
        """Проверяет уникальность типизированных идентификаторов меток."""
        if any(not isinstance(i, TagIdVO) for i in ids) or len(set(ids)) != len(ids):
            raise InvalidCatalogValueError("Метки должны быть уникальны.")

    def set_attributes(
        self,
        values: tuple[ProductAttributeValueVO, ...],
        definitions: tuple[EnumAttributeSnapshot, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет общий набор без изменения осей, default или позиций."""
        self._validate_attribute_values(values, definitions)
        self.attribute_values = tuple(sorted(values, key=lambda v: v.position))
        self._touch(actor, now)

    def set_categories(
        self,
        ids: tuple[CategoryIdVO, ...],
        primary: CategoryIdVO | None,
        existing: frozenset[CategoryIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Назначает только явные категории после проверки ссылок текущего tenant."""
        self._validate_categories(ids, primary)
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Категория отсутствует в текущем tenant.")
        self.category_ids = ids
        self.primary_category_id = primary
        self._touch(actor, now)

    def set_tags(
        self,
        ids: tuple[TagIdVO, ...],
        existing: frozenset[TagIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет метки без изменения контента и продаваемой структуры."""
        self._validate_tags(ids)
        if not set(ids).issubset(existing):
            raise InvalidCatalogValueError("Метка отсутствует в текущем tenant.")
        self.tag_ids = ids
        self._touch(actor, now)
