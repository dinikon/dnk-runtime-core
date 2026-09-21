"""Consumer behavior across historical, functional and personally selected currencies."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import unittest

from test.test_currency import services, rate, USD, EUR, UAH, DAY, NOW, TENANT
from src.modules.shared.domain.value_object.money import Money
from src.modules.price_lists.application.offer.dto.offer_dto import (
    OfferDTO,
    OfferPageDTO,
)
from src.modules.price_lists.application.offer.dto.offer_conversion_dto import (
    OfferConversionDTO,
)
from src.modules.price_lists.application.offer.service.money import OfferMoneyService
from src.modules.price_lists.domain.offer.value_object import OfferIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.infrastructure.persistence.offer_money.mapper import (
    conversion_payload,
    read_conversion,
)
from src.modules.currency.application.settings.reader import OperationCurrencySettings
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.identity.domain.user.entity import User
from src.modules.identity.application.user.command.set_display_currency_command import (
    SetDisplayCurrencyCommand,
)
from src.modules.identity.application.user.use_case.set_display_currency import (
    SetDisplayCurrencyUseCase,
)


class CurrencyConsumerTests(unittest.IsolatedAsyncioTestCase):
    def offer(self):
        return OfferDTO(
            OfferIdVO(uuid4()),
            "SKU",
            "external",
            "Item",
            "active",
            PriceListIdVO(uuid4()),
            "Supplier",
            Decimal("10.1234"),
            Decimal("15.0000"),
            "USD",
            "in_stock",
            1,
            NOW,
            None,
            None,
            1,
        )

    async def test_historical_current_and_personal_conversions_are_separate(self):
        data = services([rate(USD, UAH, "40"), rate(EUR, UAH, "50")])
        old = await data.facade.convert_to_functional(
            tenant_id=TENANT, money=Money(Decimal("10.1234"), USD), business_date=DAY
        )
        offer = self.offer()
        historical = OfferConversionDTO("converted", DAY, old)
        snapshots = SimpleNamespace(
            read_many=AsyncMock(return_value={offer.id.uuid: historical})
        )
        data.rates.rows[0] = rate(USD, UAH, "42")
        service = OfferMoneyService(
            data.facade,
            snapshots,
            data.policies,
            data.clock,
            EUR,
            failures=data.facade.failures,
            operation_id=TENANT,
        )
        page = OfferPageDTO([offer], 1, 0, 50, "offset")
        result = (await service.enrich(TENANT, page)).items[0]
        self.assertIs(result.historical_conversion, historical)
        self.assertEqual(
            result.historical_conversion.purchase_price.converted.amount,
            Decimal("404.9360"),
        )
        self.assertEqual(
            result.current_conversion.purchase_price.converted.amount,
            Decimal("425.1828"),
        )
        self.assertEqual(
            result.display_conversion.purchase_price.converted.currency, EUR
        )
        self.assertEqual(
            result.display_conversion.purchase_price.converted.amount,
            Decimal("8.503656"),
        )
        self.assertEqual(result.purchase_price, Decimal("10.1234"))
        service.display_currency = UAH
        result = (await service.enrich(TENANT, page)).items[0]
        self.assertIs(result.display_conversion, result.current_conversion)
        data.policies.enabled.return_value = {USD, UAH}
        service.display_currency = EUR
        result = (await service.enrich(TENANT, page)).items[0]
        self.assertEqual(result.display_conversion.error_code, "currency_disabled")
        self.assertEqual(result.current_conversion.status, "converted")
        self.assertIs(result.historical_conversion, historical)

    async def test_legacy_snapshot_metadata_is_not_invented(self):
        data = services([rate(USD, UAH, "40")])
        result = await data.facade.convert(
            tenant_id=TENANT, money=Money(100, USD), target=UAH, date=DAY
        )
        payload = conversion_payload(result)
        for field in (
            "purpose",
            "precision",
            "rounding_mode",
            "calculation_precision",
            "minor_units",
        ):
            payload["conversion"].pop(field)
        restored = read_conversion(payload)
        self.assertIsNone(restored.conversion.rounding_mode)
        self.assertIsNone(restored.conversion.minor_units)
        self.assertEqual(conversion_payload(restored), payload)

    async def test_missing_policy_is_frozen_and_audited_without_invented_date(self):
        data = services()
        data.policies.get.side_effect = CurrencyPolicyNotConfigured("Missing")
        settings = OperationCurrencySettings(data.policies)
        service = OfferMoneyService(
            data.facade,
            SimpleNamespace(add_many=AsyncMock()),
            settings,
            data.clock,
            failures=data.facade.failures,
            operation_id=TENANT,
        )
        state = SimpleNamespace(
            **{
                k: getattr(self.offer(), k)
                for k in ("id", "observed_at", "purchase_price", "rrp", "currency")
            }
        )
        await service.capture(TENANT, [state], operation_id=TENANT)
        command = data.facade.failures.call_args.args[0]
        self.assertIsNone(command.business_date)
        self.assertEqual(command.operation_id, TENANT)
        data.policies.get.side_effect = None
        with self.assertRaises(CurrencyPolicyNotConfigured):
            await settings.get(tenant_id=TENANT)
        self.assertEqual(data.policies.get.await_count, 1)

    async def test_historical_timezone_day_boundary(self):
        data = services([rate(USD, UAH, "40")])
        snapshots = SimpleNamespace(add_many=AsyncMock())
        service = OfferMoneyService(
            data.facade,
            snapshots,
            data.policies,
            data.clock,
            failures=data.facade.failures,
            operation_id=TENANT,
        )
        state = SimpleNamespace(
            id=OfferIdVO(uuid4()),
            observed_at=datetime(2026, 9, 20, 21, 30, tzinfo=timezone.utc),
            purchase_price=Decimal(1),
            rrp=None,
            currency="USD",
        )
        await service.capture(TENANT, [state], operation_id=TENANT)
        self.assertEqual(
            snapshots.add_many.call_args.kwargs["records"][0].conversion.business_date,
            DAY,
        )

    async def test_profile_null_inherits_and_equal_choice_is_a_noop(self):
        user = User.create_tenant_admin(tenant_id=TENANT, first_name="A", last_name="B")
        users = SimpleNamespace(
            get_by_id=AsyncMock(return_value=user), save_display_currency=AsyncMock()
        )
        validator, outbox = SimpleNamespace(validate=AsyncMock()), SimpleNamespace(
            add=AsyncMock()
        )
        use_case = SetDisplayCurrencyUseCase(
            users, validator, outbox, SimpleNamespace(now=lambda: NOW)
        )
        await use_case(SetDisplayCurrencyCommand(TENANT, user.id, EUR))
        await use_case(SetDisplayCurrencyCommand(TENANT, user.id, EUR))
        self.assertEqual(outbox.add.await_count, 1)
        await use_case(SetDisplayCurrencyCommand(TENANT, user.id, None))
        self.assertIsNone(user.display_currency)
        self.assertEqual(validator.validate.await_count, 2)
        self.assertEqual(outbox.add.await_count, 2)
