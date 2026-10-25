"""Чистые инварианты CRM без базы и HTTP."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.basket.aggregate import Basket
from src.modules.crm.domain.basket.entity.item import BasketItem
from src.modules.crm.domain.lead.aggregate import Lead
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO
from src.modules.crm.domain.lead.service.conversion_policy import LeadConversionPolicy


def identifier() -> EntityIdVO:
    """Возвращает отдельную идентичность сценария."""
    return EntityIdVO(uuid4())


class CrmSalesDomainTests(unittest.TestCase):
    def line(self, quantity: str = "1.5", price: str = "10.01") -> BasketItem:
        """Создаёт ручную строку с точным десятичным вводом."""
        return BasketItem.create(
            item_id=identifier(),
            name="Услуга",
            kind="service",
            quantity=Decimal(quantity),
            unit_price=Decimal(price),
        )

    def test_per_line_half_up_zero_and_aggregate_precision(self) -> None:
        """Не теряет копейки ни на половине копейки, ни на предельном итоге."""
        self.assertEqual(self.line().total, Decimal("15.02"))
        self.assertEqual(self.line("0.125", "0").total, Decimal("0.00"))
        self.assertEqual(
            self.line("1", "999999999999.999999").total, Decimal("1000000000000.00")
        )
        maximum = "999999999999"
        basket = Basket.create(
            basket_id=identifier(),
            owner_model_key="crm.deal",
            owner_record_id=identifier(),
            currency="UAH",
            items=tuple(self.line(maximum, maximum) for _ in range(200)),
        )
        self.assertEqual(str(basket.total), str(int(maximum) ** 2 * 200) + ".00")

    def test_invalid_values_are_rejected(self) -> None:
        """Не допускает float, отрицательные цены и недопустимые точности."""
        for quantity, price in [
            ("0", "1"),
            ("-1", "1"),
            ("1", "-0.01"),
            ("NaN", "1"),
            ("Infinity", "1"),
            ("1.0000001", "1"),
            ("1000000000000", "1"),
        ]:
            with (
                self.subTest(quantity=quantity, price=price),
                self.assertRaises(SalesError),
            ):
                self.line(quantity, price)
        with self.assertRaises(SalesError):
            BasketItem.create(
                item_id=identifier(),
                name="Товар",
                kind="product",
                quantity=1.5,
                unit_price=Decimal("1"),
            )

    def test_basket_version_frozen_and_independent_rows(self) -> None:
        """Стабильные строки сохраняются, frozen и stale не меняют состав."""
        row = self.line()
        basket = Basket.create(
            basket_id=identifier(),
            owner_model_key="crm.lead",
            owner_record_id=identifier(),
            currency="EUR",
            items=(row,),
        )
        basket.replace_items(currency="EUR", items=(row,), expected_revision=1)
        self.assertEqual(basket.revision, 1)
        basket.replace_items(
            currency="USD", items=(row, self.line()), expected_revision=1
        )
        self.assertEqual(basket.revision, 2)
        with self.assertRaises(SalesConflictError):
            basket.replace_items(currency="UAH", items=(), expected_revision=1)
        self.assertEqual(basket.currency, "USD")
        basket.freeze()
        with self.assertRaises(SalesConflictError):
            basket.replace_items(
                currency="USD", items=(), expected_revision=basket.revision
            )

    def test_position_noop_and_stale_revision(self) -> None:
        """Повтор назначения не увеличивает версию; старый запрос отклоняется."""
        position = FunnelPositionVO(identifier(), identifier())
        self.assertIs(position.move(position.funnel_id, position.stage_id, 1), position)
        moved = position.move(position.funnel_id, identifier(), 1)
        self.assertEqual(moved.revision, 2)
        with self.assertRaises(SalesConflictError):
            moved.move(moved.funnel_id, moved.stage_id, 1)

    def test_converted_lead_and_explicit_company_points(self) -> None:
        """Конвертация требует явных наборов и блокирует изменения источника."""
        point = identifier()
        with self.assertRaises(SalesError):
            LeadConversionPolicy.validate(
                "company", set(), {"company": None}, set(), (), set()
            )
        self.assertEqual(
            LeadConversionPolicy.validate(
                "company", set(), {"company": ()}, set(), (), set()
            ),
            frozenset({"company"}),
        )
        with self.assertRaises(SalesError):
            LeadConversionPolicy.validate(
                "company", set(), {"company": (point,)}, set(), (), set()
            )
        lead = Lead.create(
            record_id=identifier(),
            title="Обращение",
            position=FunnelPositionVO(identifier(), identifier()),
            actor_id=identifier(),
            now=datetime.now(UTC),
        )
        lead.complete_conversion(
            result={"mode": "company"},
            key="key",
            fingerprint="hash",
            actor_id=identifier(),
            now=datetime.now(UTC),
        )
        with self.assertRaises(SalesConflictError):
            lead.revise(
                fields={"title": "Нельзя"}, actor_id=identifier(), now=datetime.now(UTC)
            )
