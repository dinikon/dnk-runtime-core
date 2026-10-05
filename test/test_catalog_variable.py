"""Инварианты ATTRIBUTE и VARIABLE без SQL и HTTP."""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
    CreateAttributeOption,
)
from src.modules.catalog.application.attribute.command.create_attribute.handler import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
    CreateVariableVariant,
    CreateVariantSelection,
)
from src.modules.catalog.application.product.command.create_variable_product.handler import (
    CreateVariableProductHandler,
)
from src.modules.catalog.domain.attribute.aggregate import (
    Attribute,
    AttributeOption,
)
from src.modules.catalog.domain.attribute.error import InvalidAttributeError
from src.modules.catalog.domain.product.aggregate import (
    Product,
    ProductVariant,
    VariantSelection,
)
from src.modules.catalog.domain.product.error import (
    InvalidProductVariantError,
    ProductOptionUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogVariableDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.attribute = EntityIdVO(uuid4())
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())

    def variant(self, option_id, *, attribute_id=None, sku_id=None):
        return ProductVariant(
            VariantIdVO(uuid4()),
            EntityIdVO(sku_id or uuid4()),
            (VariantSelection(attribute_id or self.attribute, EntityIdVO(option_id)),),
        )

    def product(self, variants):
        return Product.create_variable(
            product_id=ProductIdVO(uuid4()),
            variants=tuple(variants),
            contents=(),
            actor_id=self.actor,
            now=self.now,
        )

    def test_attribute_codes_and_options_are_normalized_and_unique(self) -> None:
        option = AttributeOption(EntityIdVO(uuid4()), " 100 ")
        attribute = Attribute.create(
            attribute_id=EntityIdVO(uuid4()),
            code=" CAPSULES ",
            options=(option,),
            contents=(),
            actor_id=self.actor,
            now=self.now,
        )
        self.assertEqual(attribute.code, "capsules")
        self.assertEqual(attribute.options[0].code, "100")
        with self.assertRaises(InvalidAttributeError):
            Attribute.create(
                attribute_id=EntityIdVO(uuid4()),
                code="capsules",
                options=(option, AttributeOption(EntityIdVO(uuid4()), "100")),
                contents=(),
                actor_id=self.actor,
                now=self.now,
            )

    def test_variable_has_same_dimensions_and_unique_combinations(self) -> None:
        first = self.variant(uuid4())
        second = self.variant(uuid4())
        product = self.product((first, second))
        self.assertEqual(product.type, "VARIABLE")
        with self.assertRaises(InvalidProductVariantError):
            _ = product.variant
        with self.assertRaises(InvalidProductVariantError):
            self.product((first,))
        with self.assertRaises(InvalidProductVariantError):
            self.product((first, self.variant(first.selections[0].option_id.uuid)))
        with self.assertRaises(InvalidProductVariantError):
            self.product(
                (first, self.variant(uuid4(), attribute_id=EntityIdVO(uuid4())))
            )

    def test_simple_still_has_exactly_one_plain_variant(self) -> None:
        for variants in (
            (),
            (self.variant(uuid4()),),
            (
                ProductVariant(VariantIdVO(uuid4()), EntityIdVO(uuid4())),
                ProductVariant(VariantIdVO(uuid4()), EntityIdVO(uuid4())),
            ),
        ):
            with (
                self.subTest(count=len(variants)),
                self.assertRaises(InvalidProductVariantError),
            ):
                Product(
                    id=ProductIdVO(uuid4()),
                    product_type="SIMPLE",
                    variants=variants,
                    created_at=self.now,
                    updated_at=self.now,
                    created_by=self.actor,
                    updated_by=self.actor,
                )


class CatalogVariableApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.actor = EntityIdVO(uuid4())
        self.attribute_id = uuid4()
        self.options = (uuid4(), uuid4())
        self.sku_ids = (uuid4(), uuid4())
        self.repository = Mock(add=AsyncMock())
        self.skus = Mock(get_code=AsyncMock(side_effect=["SKU-1", "SKU-2"]))
        self.attributes = Mock(
            option_ids=AsyncMock(
                return_value={self.attribute_id: frozenset(self.options)}
            )
        )
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.clock = Mock(now=Mock(return_value=datetime(2026, 10, 5, tzinfo=UTC)))
        self.uuids = Mock(new=Mock(side_effect=uuid4))
        self.handler = CreateVariableProductHandler(
            self.repository,
            self.skus,
            self.attributes,
            self.locales,
            self.clock,
            self.uuids,
        )

    def command(self):
        return CreateVariableProductCommand(
            actor_id=self.actor,
            variants=tuple(
                CreateVariableVariant(
                    sku_id=self.sku_ids[index],
                    selections=(
                        CreateVariantSelection(self.attribute_id, self.options[index]),
                    ),
                )
                for index in range(2)
            ),
        )

    async def test_valid_create_and_invalid_references(self) -> None:
        result = await self.handler.execute(self.command())
        self.assertEqual(result.type, "VARIABLE")
        self.assertEqual(len(result.variants), 2)
        self.repository.add.assert_awaited_once()
        self.repository.add.reset_mock()
        self.attributes.option_ids.return_value = {}
        with self.assertRaises(ProductOptionUnavailableError):
            await self.handler.execute(self.command())
        self.repository.add.assert_not_awaited()
        self.attributes.option_ids.return_value = {
            self.attribute_id: frozenset(self.options)
        }
        self.skus.get_code.side_effect = None
        self.skus.get_code.return_value = None
        with self.assertRaises(ProductSkuNotFoundError):
            await self.handler.execute(self.command())
        self.repository.add.assert_not_awaited()

    async def test_create_attribute_uses_one_audit_time(self) -> None:
        repository = Mock(add=AsyncMock())
        handler = CreateAttributeHandler(
            repository, self.locales, self.clock, self.uuids
        )
        result = await handler.execute(
            CreateAttributeCommand(
                self.actor,
                "Capsules",
                (CreateAttributeOption("100"), CreateAttributeOption("200")),
            )
        )
        self.assertEqual(result.code, "capsules")
        self.assertEqual(result.created_at, result.updated_at)
        self.clock.now.assert_called_once()
        repository.add.assert_awaited_once()
