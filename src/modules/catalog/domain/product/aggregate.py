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
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.policy.content import ProductContentPolicy
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


class ProductKind(StrEnum):
    """Фиксированные бизнес-структуры; VARIABLE включается следующим срезом."""

    SIMPLE = "simple"
    VARIABLE = "variable"


@dataclass(slots=True)
class Product:
    """Корень SIMPLE-товара; владеет позицией и всеми переводами."""

    id: ProductIdVO
    kind: ProductKind
    product_type_id: ProductTypeIdVO
    variant: Variant
    translations: dict[str, dict[str, str]]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

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
        """Создаёт SIMPLE с ровно одной позицией без обязательного перевода."""
        return cls(
            identifier,
            ProductKind.SIMPLE,
            schema.product_type_id,
            Variant.create(variant_id, virtual),
            {},
            1,
            now,
            now,
            actor,
            actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ProductIdVO,
        kind: ProductKind,
        product_type_id: ProductTypeIdVO,
        variant: Variant,
        translations: dict[str, dict[str, str]],
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает агрегат без событий создания и исправления структуры."""
        if (
            kind != ProductKind.SIMPLE
            or revision < 1
            or not isinstance(variant, Variant)
        ):
            raise InvalidCatalogValueError("Неподдержанная структура Product.")
        for locale in translations:
            LocaleVO(locale)
        return cls(
            identifier,
            kind,
            product_type_id,
            variant,
            {k: dict(v) for k, v in translations.items()},
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def validate_content(self, schema: ProductSchemaSnapshot) -> None:
        """Проверяет оба scope во всех сохранённых локалях при смене схемы."""
        for values in self.translations.values():
            ProductContentPolicy.validate(values, schema, ContentScope.PRODUCT)
        for values in self.variant.translations.values():
            ProductContentPolicy.validate(values, schema, ContentScope.VARIANT)

    def change_type(
        self, schema: ProductSchemaSnapshot, actor: EntityIdVO, now: datetime
    ) -> None:
        """Меняет тип только после проверки всего контента без скрытой очистки."""
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
    ) -> None:
        """Проверяет и сохраняет один перевод PRODUCT либо VARIANT."""
        if schema.product_type_id != self.product_type_id:
            raise CatalogConflictError("Тип контента изменился.")
        ProductContentPolicy.validate(values, schema, scope)
        if scope == ContentScope.PRODUCT:
            self.translations[locale.value] = dict(values)
        else:
            self.variant.put_content(locale, values)
        self._touch(actor, now)

    def delete_content(
        self, locale: LocaleVO, scope: ContentScope, actor: EntityIdVO, now: datetime
    ) -> None:
        """Удаляет один перевод выбранного scope и увеличивает ревизию."""
        if scope == ContentScope.PRODUCT:
            self.translations.pop(locale.value, None)
        else:
            self.variant.delete_content(locale)
        self._touch(actor, now)

    def set_variant_properties(
        self, virtual: bool, downloadable: bool, actor: EntityIdVO, now: datetime
    ) -> None:
        """Изменяет свойства принадлежащей позиции через границу агрегата."""
        self.variant.set_properties(virtual, downloadable)
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
