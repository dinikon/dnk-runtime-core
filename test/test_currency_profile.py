"""Доменные, Application и HTTP-проверки валюты собственного профиля."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from src.config import dnk_config
from src.modules.identity.application.user.command.update_current_user_profile.command import (
    UpdateCurrentUserProfileCommand,
)
from src.modules.identity.application.user.command.update_current_user_profile.handler import (
    UpdateCurrentUserProfileHandler,
)
from src.modules.identity.application.user.query.get_current_user.query import (
    GetCurrentUserQuery,
)
from src.modules.identity.application.user.query.get_current_user.handler import (
    GetCurrentUserHandler,
)
from src.modules.identity.application.user.query.get_current_user.record_dto import (
    GetCurrentUserRecordDTO,
)
from src.modules.identity.domain.user.entity import User
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.domain.auth.error import InvalidSessionError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.infrastructure.user.currency_validator import (
    ReferenceDataProfileCurrencyValidator,
)
from src.modules.identity.infrastructure.user.tenant_currency_settings import (
    TenancyProfileCurrencySettingsAdapter,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.identity.presentation.user.depends import (
    get_current_user_handler,
    get_update_current_user_profile_handler,
)
from src.modules.identity.presentation.user.http.router import router
from src.modules.identity.presentation.user.http.request.update_current_user_profile import (
    UpdateCurrentUserProfileRequestSchema,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)

PROFILE = dict(
    last_name="Tester",
    first_name="Alice",
    middle_name=None,
    interface_language="en",
    interface_theme="dark",
    timezone="Europe/Kyiv",
)


def profile_record(user: User) -> GetCurrentUserRecordDTO:
    return GetCurrentUserRecordDTO(
        id=user.id.uuid,
        status=user.status,
        role=user.role,
        last_name=user.last_name,
        first_name=user.first_name,
        middle_name=user.middle_name,
        avatar=user.avatar,
        interface_language=user.interface_language,
        interface_theme=user.interface_theme,
        timezone=user.timezone,
        display_currency=(
            None if user.display_currency is None else user.display_currency.value
        ),
    )


class CurrencyProfileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = EntityIdVO.from_value(uuid4())
        self.user = User.create_tenant_admin(self.tenant_id, "Alice", "Tester")
        self.repo = AsyncMock()
        self.repo.get_by_id.return_value = self.user
        self.validator = AsyncMock()
        self.settings = AsyncMock()
        self.settings.get_base_currency.return_value = CurrencyVO("USD")
        self.handler = UpdateCurrentUserProfileHandler(
            self.repo, self.validator, self.settings
        )

    def command(self, **changes: object) -> UpdateCurrentUserProfileCommand:
        return replace(
            UpdateCurrentUserProfileCommand(
                tenant_id=self.tenant_id, user_id=self.user.id, **PROFILE
            ),
            **changes,
        )

    async def test_choice_omission_and_reset(self) -> None:
        first = await self.handler.execute(
            self.command(display_currency=" uah ", display_currency_provided=True)
        )
        self.assertEqual(
            (first.display_currency, first.effective_display_currency), ("UAH", "UAH")
        )
        self.assertEqual(self.user.display_currency, CurrencyVO("UAH"))
        self.validator.ensure_supported.assert_awaited_once_with(CurrencyVO("UAH"))
        self.repo.get_by_id.assert_awaited_once_with(
            self.user.id, tenant_id=self.tenant_id, for_update=True
        )
        self.validator.reset_mock()
        unchanged = await self.handler.execute(self.command())
        self.assertEqual(unchanged.display_currency, "UAH")
        self.validator.ensure_supported.assert_not_awaited()
        reset = await self.handler.execute(self.command(display_currency_provided=True))
        self.assertEqual(
            (reset.display_currency, reset.effective_display_currency), (None, "USD")
        )
        self.validator.ensure_supported.assert_not_awaited()

    async def test_malformed_and_unsupported_codes_do_not_modify_profile(self) -> None:
        for code in ("", "US", "123", "USDZ"):
            with self.subTest(code=code), self.assertRaises(DomainError):
                await self.handler.execute(
                    self.command(display_currency=code, display_currency_provided=True)
                )
        self.repo.update_profile.assert_not_awaited()
        self.assertIsNone(self.user.display_currency)
        self.validator.ensure_supported.side_effect = CurrencyCodeNotSupportedError(
            "ZZZ"
        )
        with self.assertRaises(CurrencyCodeNotSupportedError):
            await self.handler.execute(
                self.command(display_currency="ZZZ", display_currency_provided=True)
            )
        self.assertEqual(self.user.first_name, "Alice")
        self.repo.update_profile.assert_not_awaited()

    async def test_missing_settings_and_missing_or_inactive_user(self) -> None:
        self.settings.get_base_currency.side_effect = (
            TenantCurrencySettingsNotFoundError("missing")
        )
        with self.assertRaises(TenantCurrencySettingsNotFoundError):
            await self.handler.execute(self.command())
        self.repo.update_profile.assert_not_awaited()
        self.settings.get_base_currency.side_effect = None
        self.repo.get_by_id.return_value = None
        with self.assertRaises(InvalidSessionError):
            await self.handler.execute(self.command())
        self.repo.get_by_id.return_value = replace(self.user, status="blocked")
        with self.assertRaises(UserLoginUnavailableError):
            await self.handler.execute(self.command())
        self.repo.get_by_id.return_value = replace(
            self.user, tenant_id=EntityIdVO.from_value(uuid4())
        )
        with self.assertRaises(InvalidSessionError):
            await self.handler.execute(self.command())
        self.repo.update_profile.assert_not_awaited()

    async def test_domain_validates_before_any_profile_mutation(self) -> None:
        previous = replace(self.user)
        with self.assertRaises(DomainError):
            self.user.update_profile(
                **{**PROFILE, "first_name": "Changed"},
                display_currency="UAH",
                display_currency_provided=True,
            )
        self.assertEqual(self.user, previous)
        with self.assertRaises(DomainError):
            self.user.update_profile(
                **{**PROFILE, "timezone": "wrong"},
                display_currency=CurrencyVO("UAH"),
                display_currency_provided=True,
            )
        self.assertEqual(self.user, previous)
        fields = {
            field: getattr(self.user, field) for field in self.user.__dataclass_fields__
        }
        restored = User.restore(**fields)
        self.assertEqual(restored, self.user)
        with self.assertRaises(DomainError):
            User.restore(**{**fields, "display_currency": "UAH"})

    async def test_new_users_and_email_factories_preserve_bootstrap_defaults(
        self,
    ) -> None:
        self.assertIsNone(self.user.display_currency)
        self.assertEqual(self.user.role, "admin")
        email = self.user.add_email(" Alice@Example.com ", is_primary=True)
        self.assertEqual(email.email, "alice@example.com")
        with self.assertRaises(DomainError):
            self.user.add_email("other@example.com", is_primary=True)

    async def test_query_uses_projection_and_settings_for_both_preferences(
        self,
    ) -> None:
        repository = AsyncMock()
        handler = GetCurrentUserHandler(repository, self.settings)
        query = GetCurrentUserQuery(self.tenant_id, self.user.id)
        for stored, expected in ((None, "USD"), ("UAH", "UAH")):
            repository.get_current_user.return_value = replace(
                profile_record(self.user), display_currency=stored
            )
            result = await handler.execute(query)
            self.assertEqual(
                (result.display_currency, result.effective_display_currency),
                (stored, expected),
            )
        repository.get_current_user.return_value = None
        with self.assertRaises(InvalidSessionError):
            await handler.execute(query)

    async def test_adapters_call_public_scenarios(self) -> None:
        public = AsyncMock()
        await ReferenceDataProfileCurrencyValidator(public).ensure_supported(
            CurrencyVO("UAH")
        )
        self.assertEqual(public.execute.call_args.args[0].code, "UAH")
        public.execute.return_value = SimpleNamespace(base_currency="USD")
        result = await TenancyProfileCurrencySettingsAdapter(public).get_base_currency(
            self.tenant_id
        )
        self.assertEqual(result, CurrencyVO("USD"))
        self.assertEqual(
            public.execute.call_args.args[0].tenant_id.uuid, self.tenant_id.uuid
        )

    async def test_request_preserves_three_currency_states(self) -> None:
        absent = UpdateCurrentUserProfileRequestSchema(**PROFILE)
        reset = UpdateCurrentUserProfileRequestSchema(**PROFILE, display_currency=None)
        selected = UpdateCurrentUserProfileRequestSchema(
            **PROFILE, display_currency="USD"
        )
        self.assertNotIn("display_currency", absent.model_fields_set)
        self.assertIn("display_currency", reset.model_fields_set)
        self.assertEqual(selected.display_currency, "USD")

    async def test_http_choice_reset_errors_and_real_csrf(self) -> None:
        app = FastAPI()
        app.state.token_manager = TokenManager(InMemoryTokenBackend())
        app.include_router(router, prefix="/auth")
        context = RequestContext(
            principal=Principal(
                user_id=str(self.user.id.uuid),
                tenant_id=str(self.tenant_id.uuid),
                session_id="test",
            )
        )
        app.dependency_overrides[require_authenticated_request_context] = (
            lambda: context
        )
        app.dependency_overrides[get_update_current_user_profile_handler] = (
            lambda: self.handler
        )
        query_repo = AsyncMock()
        query_repo.get_current_user.side_effect = (
            lambda *args, **kwargs: profile_record(self.user)
        )
        app.dependency_overrides[get_current_user_handler] = (
            lambda: GetCurrentUserHandler(query_repo, self.settings)
        )

        @app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        from unittest.mock import patch

        with patch.object(dnk_config.AUTH, "allow_insecure_http", False):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="https://tenant.example"
            ) as client:
                response = await client.get("/auth/me")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["effective_display_currency"], "USD")
                self.assertEqual(
                    (await client.patch("/auth/me", json=PROFILE)).status_code, 403
                )
                token = (await client.get("/csrf")).json()["csrf_token"]
                headers = {"Origin": "https://tenant.example", "X-CSRF-Token": token}
                for fields, expected in (
                    ({"display_currency": " uah "}, "UAH"),
                    ({}, "UAH"),
                    ({"display_currency": None}, "USD"),
                ):
                    response = await client.patch(
                        "/auth/me", json={**PROFILE, **fields}, headers=headers
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(
                        response.json()["effective_display_currency"], expected
                    )
                self.assertEqual(
                    (
                        await client.patch(
                            "/auth/me",
                            json={**PROFILE, "display_currency": "12"},
                            headers=headers,
                        )
                    ).status_code,
                    422,
                )
                self.validator.ensure_supported.side_effect = (
                    CurrencyCodeNotSupportedError("ZZZ")
                )
                self.assertEqual(
                    (
                        await client.patch(
                            "/auth/me",
                            json={**PROFILE, "display_currency": "ZZZ"},
                            headers=headers,
                        )
                    ).status_code,
                    422,
                )
                self.settings.get_base_currency.side_effect = (
                    TenantCurrencySettingsNotFoundError("missing")
                )
                self.assertEqual((await client.get("/auth/me")).status_code, 503)
                self.assertEqual(
                    (
                        await client.patch("/auth/me", json=PROFILE, headers=headers)
                    ).status_code,
                    503,
                )
                self.assertEqual(
                    (
                        await client.patch(
                            "/auth/me",
                            json={**PROFILE, "tenant_id": str(uuid4())},
                            headers=headers,
                        )
                    ).status_code,
                    422,
                )
