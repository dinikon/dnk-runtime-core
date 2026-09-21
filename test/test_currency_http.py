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
from src.modules.currency.presentation.depends.application import (
    get_list_currencies_use_case,
    get_currency_facade,
    get_configure_currency_policy_use_case,
    get_initialize_currency_use_case,
    get_set_manual_rate_use_case,
)
from src.modules.currency.application.directory.use_case.list_currencies import (
    ListCurrenciesUseCase,
)
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.currency.domain.policy.error import CurrencyConflict
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
        self.app.dependency_overrides[get_list_currencies_use_case] = (
            lambda: ListCurrenciesUseCase(self.services.directory)
        )
        self.app.dependency_overrides[get_currency_facade] = (
            lambda: self.services.facade
        )
        self.app.dependency_overrides[get_configure_currency_policy_use_case] = (
            lambda: self.services.settings.configure
        )
        self.app.dependency_overrides[get_initialize_currency_use_case] = (
            lambda: self.services.settings.initialize
        )
        self.app.dependency_overrides[get_set_manual_rate_use_case] = (
            lambda: self.services.settings.set_manual_rate
        )
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

    async def test_booking_precision_and_expected_failures_have_explicit_codes(self):
        response = await self.client.post(
            "/api/console/currency/convert",
            json={
                "amount": "1.0001",
                "source_currency": "USD",
                "target_currency": "UAH",
                "business_date": DAY.isoformat(),
                "purpose": "booking",
                "precision": 3,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["converted"]["amount"], "41.254")
        self.assertEqual(response.json()["conversion"]["precision"], 3)
        self.services.policies.enabled.return_value = {UAH}
        response = await self.client.post(
            "/api/console/currency/convert",
            json={
                "amount": "1",
                "source_currency": "USD",
                "target_currency": "UAH",
                "business_date": DAY.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["code"], "currency_disabled")

    async def test_identity_preference_is_scoped_to_authenticated_member(self):
        from src.modules.identity.presentation.http.console_auth.controller.set_display_currency import (
            router as profile_router,
        )
        from src.modules.identity.presentation.depends.display_currency import (
            get_set_display_currency_use_case,
        )
        from src.modules.identity.application.user.dto.display_currency_dto import (
            DisplayCurrencyDTO,
        )

        self.app.include_router(profile_router, prefix="/api/console/auth")
        change = AsyncMock(return_value=DisplayCurrencyDTO(USD))
        self.app.dependency_overrides[get_set_display_currency_use_case] = (
            lambda: change
        )
        self.principal = Principal(str(TENANT), str(TENANT), "session", ("member",))
        response = await self.client.put(
            "/api/console/auth/me/display-currency", json={"display_currency": "USD"}
        )
        self.assertEqual(response.status_code, 403)
        self.app.dependency_overrides[require_csrf] = lambda: None
        response = await self.client.put(
            "/api/console/auth/me/display-currency",
            json={"display_currency": "USD", "user_id": "another-user"},
        )
        self.assertEqual(response.status_code, 422)
        response = await self.client.put(
            "/api/console/auth/me/display-currency", json={"display_currency": "USD"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        command = change.call_args.args[0]
        self.assertEqual(command.tenant_id, TENANT)
        self.assertEqual(command.user_id.uuid, TENANT.uuid)
        self.assertEqual(command.currency, USD)
        change.return_value = DisplayCurrencyDTO(None)
        response = await self.client.put(
            "/api/console/auth/me/display-currency", json={"display_currency": None}
        )
        self.assertEqual(response.json(), {"display_currency": None})

    async def test_unexpected_exceptions_are_not_hidden_as_business_conflicts(self):
        self.app.dependency_overrides[require_csrf] = lambda: None
        self.services.settings.configure.side_effect = RuntimeError(
            "Programming failure"
        )
        with self.assertRaisesRegex(RuntimeError, "Programming failure"):
            await self.client.put(
                "/api/console/currency/policy", json=self.policy_payload()
            )
