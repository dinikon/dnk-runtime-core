"""Инварианты представления и точные значения заполненного Draft."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.error import ChannelsConflictError
from src.modules.channels.infrastructure.product_representation.adapter.catalog import (
    exact_decimal,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ChannelsBindingDomainTests(unittest.TestCase):
    """Не подменяет тестирование Domain успешным SQL результатом."""

    def test_root_enforces_connection_cardinality_and_revision(self) -> None:
        """Нельзя привязать чужой ресурс, вторую активную публикацию или старую версию."""
        root, connection, item, actor = (EntityIdVO(uuid4()) for _ in range(4))
        representation = ProductRepresentation.create(root, connection, item)
        now = datetime.now(UTC)
        with self.assertRaises(ChannelsConflictError):
            representation.bind(
                EntityIdVO(uuid4()),
                EntityIdVO(uuid4()),
                EntityIdVO(uuid4()),
                1,
                actor,
                now,
            )
        first = representation.bind(
            EntityIdVO(uuid4()), EntityIdVO(uuid4()), connection, 1, actor, now
        )
        with self.assertRaises(ChannelsConflictError):
            representation.bind(
                EntityIdVO(uuid4()),
                EntityIdVO(uuid4()),
                connection,
                representation.revision,
                actor,
                now,
            )
        with self.assertRaises(ChannelsConflictError):
            representation.unbind(first.id, 1, actor, now)
        representation.unbind(first.id, representation.revision, actor, now)
        self.assertIsNone(representation.active_binding())
        self.assertEqual(len(representation.bindings), 1)
        with self.assertRaises(ChannelsConflictError):
            representation.bind(
                first.id,
                EntityIdVO(uuid4()),
                connection,
                representation.revision,
                actor,
                now,
            )
        second = representation.bind(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            connection,
            representation.revision,
            actor,
            now,
        )
        with self.assertRaises(ChannelsConflictError):
            ProductRepresentation.restore(root, connection, item, 0, [second])

    def test_decimal_normalization_never_rounds_with_a_small_context(self) -> None:
        """Удаление незначащих нулей не округляет значимые цифры precision context."""
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(
                str(exact_decimal(Decimal("9007199254740993.123456000000"))),
                "9007199254740993.123456",
            )
            self.assertEqual(exact_decimal(Decimal("1.1234567")), Decimal("1.1234567"))

    def test_stock_conversion_preserves_unknown_fraction_and_range(self) -> None:
        """Не округляет дроби и не превращает unknown в доступный товар."""
        for quantity in (Decimal("1.25"), Decimal("NaN"), Decimal("2147483648")):
            with self.assertRaises(InvalidCatalogValueError):
                StockSpecificationVO.from_declared_values(True, quantity, None, "no")
        with self.assertRaises(InvalidCatalogValueError):
            StockSpecificationVO.from_declared_values(False, None, None, "no")
        stock = StockSpecificationVO.from_declared_values(
            True, Decimal("0E-12"), None, "no"
        )
        self.assertEqual(stock.stock_quantity, 0)
        self.assertEqual(stock.effective_status().value, "out_of_stock")
