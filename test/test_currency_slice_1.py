"""Первый срез: денежные VO, проверка валют, onboarding и HTTP-контекст."""

from dataclasses import FrozenInstanceError
from decimal import Decimal, Inexact, localcontext
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO, CurrencyVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.domain.value_object.money_error import (
    InvalidMoneyError,
    MoneyCurrencyMismatchError,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant.command.create_tenant.command import (
    CreateTenantCommand,
)
from src.modules.tenancy.application.tenant.command.create_tenant.handler import (
    CreateTenantHandler,
)
from src.modules.tenancy.application.tenant.onboarding import TenantOnboardingService
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.dto import (
    GetTenantCurrencySettingsResultDTO,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.handler import (
    GetTenantCurrencySettingsHandler,
)
from src.modules.tenancy.application.tenant_currency_settings.query.get_tenant_currency_settings.query import (
    GetTenantCurrencySettingsQuery,
)
from src.modules.tenancy.domain.tenant.entity import Tenant
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    InvalidTenantBaseCurrencyError,
    TenantCurrencySettingsNotFoundError,
)
from src.modules.tenancy.infrastructure.adapter.currency_validator import (
    ReferenceDataCurrencyValidator,
)
from src.modules.tenancy.domain.tenant_currency_settings.aggregate import (
    TenantCurrencySettings,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.mapper import (
    TenantCurrencySettingsMapper,
)
from src.modules.tenancy.presentation.http.router import router
from src.modules.tenancy.presentation.tenant_currency_settings.depends import (
    get_tenant_currency_settings_handler,
)


class MoneyValueObjectTests(unittest.TestCase):
    def test_currency_normalization_identity_and_legacy_import(self) -> None:
        currency = CurrencyVO.from_value(" jpy ")
        self.assertEqual(currency.value, "JPY")
        self.assertEqual(str(currency), "JPY")
        self.assertIs(CurrencyVO.from_value(currency), currency)
        self.assertIs(CurrencyCodeVO, CurrencyVO)
        from src.modules.shared import CurrencyCodeVO as LegacyCurrency

        self.assertEqual(LegacyCurrency.from_value("jpy"), currency)
        with self.assertRaises(FrozenInstanceError):
            currency.value = "USD"

    def test_invalid_currency_shape_is_domain_error(self) -> None:
        for value in (None, 123, "US", "USDD", "U1D", "€UR", "ßD", ""):
            with (
                self.subTest(value=value),
                self.assertRaises(CurrencyCodeNotSupportedError),
            ):
                CurrencyVO.from_value(value)

    def test_signed_money_rounding_and_ambient_context_independence(self) -> None:
        usd = CurrencyVO("USD")
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            positive = MoneyVO(Decimal("12345.23455"), usd)
            negative = MoneyVO(Decimal("-12345.23455"), usd)
            self.assertEqual(positive.amount, Decimal("12345.2346"))
            self.assertEqual(negative.amount, Decimal("-12345.2346"))
            self.assertEqual((positive + negative).amount, Decimal("0.0000"))
            self.assertEqual(
                (positive - MoneyVO(Decimal("20000"), usd)).amount,
                Decimal("-7654.7654"),
            )
        self.assertFalse(MoneyVO(Decimal("-0.00001"), usd).amount.is_signed())
        with self.assertRaises(FrozenInstanceError):
            positive.amount = Decimal("1")

    def test_money_rejects_invalid_input_and_overflow_after_rounding(self) -> None:
        usd = CurrencyVO("USD")
        for amount in (
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            Decimal("1000000000000000"),
            Decimal("-1000000000000000"),
            Decimal("999999999999999.99995"),
            Decimal("-999999999999999.99995"),
            1.5,
            "1",
            True,
        ):
            with self.subTest(amount=amount), self.assertRaises(InvalidMoneyError):
                MoneyVO(amount, usd)
        with self.assertRaises(InvalidMoneyError):
            MoneyVO(Decimal("1"), "USD")
        maximum = MoneyVO(Decimal("999999999999999.9999"), usd)
        with self.assertRaises(InvalidMoneyError):
            maximum + MoneyVO(Decimal("0.0001"), usd)
        with self.assertRaises(InvalidMoneyError):
            maximum - MoneyVO(Decimal("-0.0001"), usd)

    def test_money_rejects_arithmetic_across_currencies(self) -> None:
        usd = MoneyVO(Decimal("1"), CurrencyVO("USD"))
        uah = MoneyVO(Decimal("1"), CurrencyVO("UAH"))
        with self.assertRaises(MoneyCurrencyMismatchError):
            usd + uah
        with self.assertRaises(MoneyCurrencyMismatchError):
            usd - uah

    def test_settings_factories_and_mapper_preserve_readonly_currency(self) -> None:
        settings = TenantCurrencySettings.create(base_currency=CurrencyVO("USD"))
        restored = TenantCurrencySettingsMapper.to_domain(
            TenantCurrencySettingsMapper.to_update_values(settings)
        )
        self.assertEqual(restored.base_currency, CurrencyVO("USD"))
        with self.assertRaises(AttributeError):
            restored.base_currency = CurrencyVO("EUR")
        with self.assertRaises(InvalidTenantBaseCurrencyError):
            TenantCurrencySettings.create(base_currency="USD")


class CurrencyApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_currency_normalizes_and_returns_own_dto(self) -> None:
        dto = ValidateCurrencyResultDTO("JPY", "392", 0)
        repository = AsyncMock()
        repository.get_active.return_value = dto
        result = await ValidateCurrencyHandler(repository).execute(
            ValidateCurrencyQuery(" jpy ")
        )
        self.assertEqual(result, dto)
        repository.get_active.assert_awaited_once_with("JPY")

    async def test_validate_currency_rejects_missing_or_inactive(self) -> None:
        repository = AsyncMock()
        repository.get_active.return_value = None
        with self.assertRaises(CurrencyCodeNotSupportedError):
            await ValidateCurrencyHandler(repository).execute(
                ValidateCurrencyQuery("ZZZ")
            )
        repository.get_active.reset_mock()
        with self.assertRaises(CurrencyCodeNotSupportedError):
            await ValidateCurrencyHandler(repository).execute(
                ValidateCurrencyQuery("US")
            )
        repository.get_active.assert_not_awaited()

    async def test_onboarding_checks_currency_before_all_side_effects(self) -> None:
        for code in ("USD", "UAH"):
            with self.subTest(code=code):
                handler, dependencies = self.make_create_handler(supported=False)
                with self.assertRaises(CurrencyCodeNotSupportedError):
                    await handler.execute(self.create_command(code))
                for dependency in dependencies:
                    for name in (
                        "add",
                        "bootstrap",
                        "register",
                        "create_tenant_admin",
                        "initialize",
                    ):
                        getattr(dependency, name).assert_not_awaited()

    async def test_successful_onboarding_passes_validated_currency_to_tenant(
        self,
    ) -> None:
        handler, dependencies = self.make_create_handler(supported=True)
        result = await handler.execute(self.create_command(" usd "))
        settings = dependencies[5].initialize.call_args.args[1]
        self.assertEqual(settings.base_currency, CurrencyVO("USD"))
        self.assertEqual(result.base_currency, "USD")
        dependencies[2].bootstrap.assert_awaited_once()
        dependencies[3].register.assert_awaited_once()
        dependencies[4].create_tenant_admin.assert_awaited_once()

    async def test_missing_tenant_settings_is_explicit_error(self) -> None:
        repository = AsyncMock()
        repository.get_currency_settings.return_value = None
        with self.assertRaises(TenantCurrencySettingsNotFoundError):
            await GetTenantCurrencySettingsHandler(repository).execute(
                GetTenantCurrencySettingsQuery(Tenant.create("Acme", "acme").id)
            )

    def make_create_handler(
        self, *, supported: bool
    ) -> tuple[CreateTenantHandler, list[AsyncMock]]:
        tenants, domains, bootstrap, storage, identity, settings_writer = [
            AsyncMock() for _ in range(6)
        ]
        tenants.exists_by_external_id.return_value = False
        domains.exists_by_host.return_value = False
        identity.create_tenant_admin.return_value = type(
            "Provisioned",
            (),
            {"user_id": uuid4(), "user_email_id": uuid4(), "user_status": "active"},
        )()
        currencies = AsyncMock()
        currencies.get_active.side_effect = (
            (lambda code: ValidateCurrencyResultDTO(code, "840", 2))
            if supported
            else (lambda code: None)
        )
        handler = CreateTenantHandler(
            TenantOnboardingService(tenants, domains),
            identity,
            TenantSchemaBootstrapContextFactory(schema_prefix="dnk_"),
            bootstrap,
            storage,
            ReferenceDataCurrencyValidator(ValidateCurrencyHandler(currencies)),
            settings_writer,
            AsyncMock(),
        )
        return handler, [
            tenants,
            domains,
            bootstrap,
            storage,
            identity,
            settings_writer,
        ]

    def create_command(self, code: str) -> CreateTenantCommand:
        return CreateTenantCommand(
            tenant_name="Acme",
            external_id="acme",
            tenant_domain_host="acme.example.com",
            user_first_name="Alice",
            user_last_name="Doe",
            user_email="alice@example.com",
            base_currency=code,
        )


class TenantCurrencySettingsHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_context_selects_only_its_tenant(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        repository = AsyncMock()
        repository.get_currency_settings.return_value = (
            GetTenantCurrencySettingsResultDTO("USD")
        )
        app.dependency_overrides[get_tenant_currency_settings_handler] = (
            lambda: GetTenantCurrencySettingsHandler(repository)
        )
        tenant_id = uuid4()
        context = RequestContext(
            Principal(str(uuid4()), str(tenant_id), "session", ("member",)),
            None,
            None,
            None,
        )
        app.dependency_overrides[require_authenticated_request_context] = (
            lambda: context
        )
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/console/tenants/current/currency-settings",
                params={"tenant_id": str(uuid4())},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"base_currency": "USD"})
            self.assertEqual(
                repository.get_currency_settings.call_args.args[0].uuid, tenant_id
            )
            repository.get_currency_settings.return_value = None
            self.assertEqual(
                (
                    await client.get("/api/console/tenants/current/currency-settings")
                ).status_code,
                404,
            )
            app.dependency_overrides[require_authenticated_request_context] = (
                lambda: RequestContext(
                    Principal(str(uuid4()), None, "session", ("member",)),
                    None,
                    None,
                    None,
                )
            )
            self.assertEqual(
                (
                    await client.get("/api/console/tenants/current/currency-settings")
                ).status_code,
                403,
            )

    async def test_anonymous_request_is_rejected(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        handler = AsyncMock()
        app.dependency_overrides[get_tenant_currency_settings_handler] = lambda: handler
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/console/tenants/current/currency-settings"
            )
        self.assertEqual(response.status_code, 401)
        handler.execute.assert_not_awaited()
