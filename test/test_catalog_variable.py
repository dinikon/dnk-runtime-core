"""Доменные проверки enum-справочника, VARIABLE и безопасных переходов."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.aggregate import Product, ProductKind
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.entity.structure import (
    SimpleProductStructure,
    VariableProductStructure,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.product.value_object.axis import VariationAxis
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.product.value_object.schema import ProductSchemaSnapshot
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope
from src.modules.catalog.domain.product.policy.title import VariantTitlePolicy
from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


class CatalogVariableDomainTests(unittest.TestCase):
    """Проверяет правила Product независимо от SQL и HTTP."""

    def setUp(self) -> None:
        """Готовит ось и две уникальные продаваемые позиции."""
        self.now = datetime.now(UTC)
        self.actor = EntityIdVO(uuid4())
        self.attribute = AttributeIdVO(uuid4())
        self.options = tuple(AttributeOptionIdVO(uuid4()) for _ in range(3))
        self.axis = VariationAxis(self.attribute, self.options, 0)
        self.definitions = (
            EnumAttributeSnapshot(self.attribute, frozenset(self.options)),
        )
        self.schema = ProductSchemaSnapshot(ProductTypeIdVO(uuid4()), 1, ())
        self.variants = tuple(
            Variant.create(
                VariantIdVO(uuid4()),
                bool(i),
                VariationSelectionVO(((self.attribute, o),)),
            )
            for i, o in enumerate(self.options[:2])
        )
        self.structure = VariableProductStructure.create(
            (self.axis,), self.variants[0].selection, self.variants
        )
        self.product = Product.create_variable(
            ProductIdVO(uuid4()),
            self.schema,
            self.structure,
            self.definitions,
            self.actor,
            self.now,
        )

    def test_variable_validates_full_unique_combinations_and_default(self) -> None:
        """Неполные, повторные, чужие и несуществующие default-комбинации отклоняются."""
        bad = [
            replace(self.structure, variants=self.variants[:1]),
            replace(self.structure, axes=()),
            replace(
                self.structure,
                variants=(
                    self.variants[0],
                    Variant.create(
                        VariantIdVO(uuid4()), False, self.variants[0].selection
                    ),
                ),
            ),
            replace(
                self.structure,
                variants=(
                    self.variants[0],
                    Variant.create(VariantIdVO(uuid4()), False),
                ),
            ),
            replace(
                self.structure,
                default_selection=VariationSelectionVO(
                    ((self.attribute, self.options[2]),)
                ),
            ),
            replace(self.structure, axes=(self.axis, self.axis)),
        ]
        for structure in bad:
            with (
                self.subTest(structure=structure),
                self.assertRaises(InvalidCatalogValueError),
            ):
                Product.create_variable(
                    ProductIdVO(uuid4()),
                    self.schema,
                    structure,
                    self.definitions,
                    self.actor,
                    self.now,
                )
        with self.assertRaises(InvalidCatalogValueError):
            Product.create_variable(
                ProductIdVO(uuid4()),
                self.schema,
                self.structure,
                (EnumAttributeSnapshot(self.attribute, frozenset(self.options[:1])),),
                self.actor,
                self.now,
            )

    def test_replacement_preserves_ids_content_and_rejects_loss(self) -> None:
        """Сохранённые переводы не заменяются пустыми данными редактора структуры."""
        variant = self.variants[0]
        self.product.put_content(
            LocaleVO("en"),
            {},
            self.schema,
            ContentScope.VARIANT,
            self.actor,
            self.now,
            variant.id,
        )
        replacement = VariableProductStructure.create(
            (self.axis,),
            None,
            tuple(
                Variant.create(v.id, not v.virtual, v.selection) for v in self.variants
            ),
        )
        self.product.replace_variants(
            replacement, self.definitions, self.schema, self.actor, self.now
        )
        self.assertEqual(self.product.find_variant(variant.id).translations, {"en": {}})
        revision = self.product.revision
        removed = VariableProductStructure.create(
            (self.axis,),
            None,
            (
                self.variants[1],
                Variant.create(
                    VariantIdVO(uuid4()),
                    False,
                    VariationSelectionVO(((self.attribute, self.options[2]),)),
                ),
            ),
        )
        with self.assertRaises(CatalogConflictError):
            self.product.replace_variants(
                removed, self.definitions, self.schema, self.actor, self.now
            )
        self.assertEqual(self.product.revision, revision)
        self.assertEqual(self.product.find_variant(variant.id).translations, {"en": {}})

    def test_explicit_kind_transition_preserves_product_and_variant_identity(
        self,
    ) -> None:
        """Переход в SIMPLE требует пустого VARIANT-контента, но сохраняет PRODUCT."""
        variant = self.variants[0]
        self.product.put_content(
            LocaleVO("en"), {}, self.schema, ContentScope.PRODUCT, self.actor, self.now
        )
        self.product.put_content(
            LocaleVO("en"),
            {},
            self.schema,
            ContentScope.VARIANT,
            self.actor,
            self.now,
            variant.id,
        )
        target = SimpleProductStructure.create(Variant.create(variant.id, False))
        with self.assertRaises(InvalidCatalogValueError):
            self.product.change_kind(
                ProductKind.SIMPLE, target, (), self.schema, self.actor, self.now
            )
        self.product.delete_content(
            LocaleVO("en"), ContentScope.VARIANT, self.actor, self.now, variant.id
        )
        self.product.change_kind(
            ProductKind.SIMPLE, target, (), self.schema, self.actor, self.now
        )
        self.assertEqual(self.product.variants[0].id, variant.id)
        self.assertEqual(self.product.translations, {"en": {}})
        self.product.change_kind(
            ProductKind.VARIABLE,
            self.structure,
            self.definitions,
            self.schema,
            self.actor,
            self.now,
        )
        self.assertEqual(self.product.translations, {"en": {}})

    def test_restore_checks_cardinality_kind_and_combinations(self) -> None:
        """Восстановление проверяет инварианты в Product, а не mapper."""
        fields = {
            k: getattr(self.product, k)
            for k in [
                "kind",
                "product_type_id",
                "structure",
                "translations",
                "revision",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            ]
        }
        fields["identifier"] = self.product.id
        self.assertEqual(len(Product.restore(**fields).variants), 2)
        for structure in [
            SimpleProductStructure.restore(self.variants),
            VariableProductStructure.restore(
                (self.axis,), None, (self.variants[0], self.variants[0])
            ),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                Product.restore(**{**fields, "structure": structure})

    def test_simple_restore_rejects_extra_positions_axes_and_defaults(self) -> None:
        """SIMPLE проверяется агрегатом без потери хранимых частей в mapper."""
        plain = Variant.create(VariantIdVO(uuid4()), False)
        for structure in (
            SimpleProductStructure.restore(()),
            SimpleProductStructure.restore((plain, plain)),
            SimpleProductStructure.restore((plain,), (self.axis,)),
            SimpleProductStructure.restore((plain,), (), self.variants[0].selection),
        ):
            with (
                self.subTest(structure=structure),
                self.assertRaises(InvalidCatalogValueError),
            ):
                Product.restore(
                    identifier=self.product.id,
                    kind=ProductKind.SIMPLE,
                    product_type_id=self.schema.product_type_id,
                    structure=structure,
                    translations={},
                    revision=1,
                    created_at=self.now,
                    updated_at=self.now,
                    created_by=self.actor,
                    updated_by=self.actor,
                )

    def test_title_policy_distinguishes_absence_override_and_empty_value(self) -> None:
        """Пустой override не теряется, другой scope и описание не наследуются."""
        self.assertEqual(
            VariantTitlePolicy.resolve("title", {"title": "Product"}, None),
            ("Product", ContentScope.PRODUCT),
        )
        self.assertEqual(
            VariantTitlePolicy.resolve("title", {"title": "Product"}, {"title": ""}),
            ("", ContentScope.VARIANT),
        )
        self.assertEqual(VariantTitlePolicy.resolve("title", None, {}), (None, None))
        self.assertEqual(
            VariantTitlePolicy.resolve(None, {"description": "Text"}, None),
            (None, None),
        )

    def test_attribute_options_preserve_identity_and_protect_usage(self) -> None:
        """Удаление используемого option и смена кода отклоняются до изменения."""
        option = AttributeOption.create(self.options[0], "red", LocaleVO("en"), "Red")
        entity = AttributeDefinition.create(
            self.attribute,
            "color",
            LocaleVO("en"),
            "Color",
            (option,),
            self.actor,
            self.now,
        )
        with self.assertRaises(CatalogConflictError):
            entity.replace_options((), frozenset((option.id,)), self.actor, self.now)
        with self.assertRaises(CatalogConflictError):
            entity.replace_options(
                (AttributeOption.restore(option.id, "green", {"en": "Green"}),),
                frozenset(),
                self.actor,
                self.now,
            )
        entity.replace_options(
            (option.translated(LocaleVO("ru"), "Красный"),),
            frozenset((option.id,)),
            self.actor,
            self.now,
        )
        self.assertEqual(entity.options[0].translations, {"en": "Red", "ru": "Красный"})
        self.assertEqual(entity.options[0].id, option.id)
