from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest

from fastapi import FastAPI
import httpx

from src.modules.shared.domain.identity_context import Principal, RequestContext
from src.modules.shared.presentation.identity_context.depends import (
    get_optional_request_context,
)
from src.modules.shared.presentation.tokens.depends import get_token_manager
from src.modules.currency.presentation.http.router import router
from src.modules.currency.presentation.depends import get_currency_services
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.currency.domain.errors import CurrencyConflict
from test.test_currency import services, rate, TENANT, USD, UAH, DAY


class CurrencyHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/console")
        self.principal = Principal(str(TENANT), str(TENANT), "test-session", ("admin",))
        self.services = services([rate(USD, UAH, "41.25")])
        self.services.settings = SimpleNamespace(
            initialize=AsyncMock(), configure=AsyncMock(), set_manual_rate=AsyncMock()
        )
        self.app.dependency_overrides[get_currency_services] = lambda: self.services
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: RequestContext(self.principal, None, None, None)
        )
        self.app.dependency_overrides[get_token_manager] = lambda: SimpleNamespace(
            get_token=AsyncMock(return_value=None)
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="https://currency.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    def policy_payload(self):
        return dict(
            default_transaction_currency="UAH",
            provider_code="NBU",
            rate_date_policy="previous_available",
            rounding_mode="ROUND_HALF_UP",
            allow_cross_rate=True,
            bridge_currency="UAH",
            business_timezone="Europe/Kyiv",
            expected_version=1,
        )

    async def test_unauthenticated_and_member_write_denied(self):
        self.principal = None
        response = await self.client.get("/api/console/currency/directory")
        self.assertEqual(response.status_code, 401)
        self.principal = Principal(str(TENANT), str(TENANT), "session", ("member",))
        self.app.dependency_overrides[require_csrf] = lambda: None
        self.assertEqual(
            (await self.client.get("/api/console/currency/directory")).status_code, 200
        )
        response = await self.client.put(
            "/api/console/currency/policy", json=self.policy_payload()
        )
        self.assertEqual(response.status_code, 403)
        self.services.settings.configure.assert_not_called()

    async def test_csrf_is_required_for_mutations(self):
        response = await self.client.put(
            "/api/console/currency/policy", json=self.policy_payload()
        )
        self.assertEqual(response.status_code, 403)
        self.services.settings.configure.assert_not_called()

    async def test_tenant_cannot_be_supplied_and_conflict_is_typed(self):
        self.app.dependency_overrides[require_csrf] = lambda: None
        response = await self.client.put(
            "/api/console/currency/policy",
            json={**self.policy_payload(), "tenant_id": str(TENANT)},
        )
        self.assertEqual(response.status_code, 422)
        self.services.settings.configure.side_effect = CurrencyConflict("Reload")
        response = await self.client.put(
            "/api/console/currency/policy", json=self.policy_payload()
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "currency_conflict")
        self.assertEqual(
            self.services.settings.configure.call_args.args[0].tenant_id, TENANT
        )

    async def test_money_wire_values_are_decimal_strings(self):
        response = await self.client.post(
            "/api/console/currency/convert",
            json=dict(
                amount="100",
                source_currency="USD",
                target_currency="UAH",
                business_date=DAY.isoformat(),
            ),
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["converted"], {"amount": "4125.00", "currency": "UAH"})
        self.assertIsInstance(result["conversion"]["rate"], str)
        response = await self.client.post(
            "/api/console/currency/convert",
            json=dict(
                amount=100.1, source_currency="USD", business_date=DAY.isoformat()
            ),
        )
        self.assertEqual(response.status_code, 422)
