"""Контракты пакетов, состояние агрегата и защита секретов Channels."""

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from cryptography.fernet import Fernet
import httpx
from pydantic import ValidationError

from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.connection import Connection
from src.modules.channels.domain.channel.error import (
    ChannelNotFoundError,
    InvalidChannelNameError,
    InvalidChannelStateError,
    InvalidResourceIdentityError,
)
from src.modules.channels.domain.channel.error import (
    ChannelRevisionConflictError,
)
from src.modules.channels.domain.channel.value_object.channel_name import ChannelNameVO
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.http import PublicHttpsTransport, SafeJsonHttp
from src.modules.channels.infrastructure.platforms.prom.models import PromConfig
from src.modules.channels.infrastructure.platforms.rozetka.models import (
    RozetkaConfig,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.http.access import channel_http_error
from src.modules.channels.presentation.channel.http.request.update_channel import (
    UpdateChannelRequest,
)
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher

FIXTURES = Path(__file__).parent / "fixtures/channels"


class FixtureHttp:
    """Транспорт контрактов, сохраняющий вызовы только внутри теста."""

    def __init__(self, responses: list[object]) -> None:
        """Принимает последовательность подготовленных ответов транспорта."""
        self.responses, self.calls = list(responses), []

    async def request(self, method: str, url: str, **kwargs: object) -> object:
        """Возвращает подготовленный ответ без обращения к внешней площадке."""
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ChannelPlatformTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет контракты платформ и безопасный HTTP transport."""

    async def test_three_typed_contracts_and_capability_declarations(self) -> None:
        """Различает identity пользователя и магазина и сохраняет WordPress subpath."""
        cases = [
            (
                "prom",
                "https://my.prom.ua",
                {},
                {"token": "secret-prom"},
                "prom-groups.json",
                ResourceIdentityVO(namespace="prom.root_group", key="7101"),
            ),
            (
                "rozetka",
                "https://api-seller.rozetka.com.ua",
                {},
                {"token": "secret-roz"},
                "rozetka-login.json",
                ResourceIdentityVO(namespace="rozetka.market", key="1086"),
            ),
            (
                "woocommerce",
                "https://SHOP.example:443/wordpress/",
                {},
                {"consumer_key": "ck-test", "consumer_secret": "cs-test"},
                "woocommerce-system-status.json",
                ResourceIdentityVO(
                    namespace="woocommerce.site", key="https://shop.example/wordpress"
                ),
            ),
        ]
        for kind, endpoint, settings, secrets, file, expected in cases:
            http = FixtureHttp([json.loads((FIXTURES / file).read_text())])
            platform = InstalledPlatforms(http).get(kind)
            validated = platform.validate(
                ConnectionConfigVO.create(
                    version=1, endpoint=endpoint, settings=settings
                ),
                secrets,
            )
            self.assertEqual(
                await platform.verify(validated.config, validated.credentials), expected
            )
            self.assertEqual(
                platform.manifest.supported_capabilities,
                ("verify_connection", "publications", "read_stock", "write_stock")
                + (
                    ("write_content",)
                    if kind == "woocommerce"
                    else ("content_feed",) if kind == "prom" else ()
                ),
            )
            self.assertNotIn("secret-", repr(validated))
            self.assertNotIn("secret-", repr(platform.manifest))
            self.assertTrue(http.calls[0][1].startswith(validated.config.endpoint))
        self.assertIn("/wordpress/wp-json/wc/v3/system_status", http.calls[0][1])
        self.assertNotIn("cs-test", http.calls[0][1])

    async def test_concrete_configs_and_unmasked_credentials(self) -> None:
        """Шифруемый JSON содержит реальные секреты каждого конкретного пакета."""
        registry = InstalledPlatforms()
        for kind, model, endpoint, settings, credentials in (
            ("prom", PromConfig, "https://my.prom.ua", {}, {"token": "секрет-prom"}),
            (
                "rozetka",
                RozetkaConfig,
                "https://api-seller.rozetka.com.ua",
                {},
                {"token": "секрет-rozetka"},
            ),
            (
                "woocommerce",
                WooCommerceConfig,
                "https://SHOP.example:443/wordpress/",
                {},
                {"consumer_key": "ключ", "consumer_secret": "секрет"},
            ),
        ):
            with self.subTest(kind=kind):
                platform = registry.get(kind)
                config = ConnectionConfigVO.create(
                    version=1, endpoint=endpoint, settings=settings
                )
                self.assertIsInstance(platform.decode_config(config), model)
                validated = platform.validate(config, credentials)
                self.assertEqual(json.loads(validated.credentials), credentials)
                cipher = FernetCipher(Fernet.generate_key().decode())
                self.assertEqual(
                    json.loads(cipher.decrypt(cipher.encrypt(validated.credentials))),
                    credentials,
                )
                self.assertIsNone(platform.validate(validated.config, None).credentials)
                with self.assertRaises(ChannelInputError) as error:
                    platform.validate(
                        validated.config, credentials | {"secret-field": "secret-input"}
                    )
                self.assertEqual(error.exception.field, "credentials")
                self.assertNotIn("secret-", str(error.exception))

    async def test_prom_missing_ambiguous_repeated_and_paginated_groups(self) -> None:
        """Не выбирает случайную группу и не подтверждает неполный обход."""
        for pages in [
            [{"groups": []}],
            [
                {
                    "groups": [
                        {"id": 1, "parent_group_id": None},
                        {"id": 2, "parent_group_id": None},
                    ]
                }
            ],
            [{"groups": [{"id": 0, "parent_group_id": None}]}],
        ]:
            p = InstalledPlatforms(FixtureHttp(pages)).get("prom")
            v = p.validate(
                ConnectionConfigVO.create(
                    version=1, endpoint="https://my.prom.ua", settings={}
                ),
                {"token": "test"},
            )
            with self.assertRaises(VerificationFailure) as error:
                await p.verify(v.config, v.credentials)
            self.assertEqual(error.exception.code, "resource_identity_unavailable")
        first = {
            "groups": [
                {"id": i, "parent_group_id": None if i == 200 else 200}
                for i in range(200, 100, -1)
            ]
        }
        http = FixtureHttp([first, {"groups": []}])
        p = InstalledPlatforms(http).get("prom")
        v = p.validate(
            ConnectionConfigVO.create(
                version=1, endpoint="https://my.prom.ua", settings={}
            ),
            {"token": "test"},
        )
        self.assertEqual((await p.verify(v.config, v.credentials)).key, "200")
        self.assertIn("last_id=101", http.calls[1][1])
        p = InstalledPlatforms(FixtureHttp([first, first])).get("prom")
        with self.assertRaises(VerificationFailure):
            await p.verify(v.config, v.credentials)

    async def test_rozetka_http_200_auth_failure_is_not_verified(self) -> None:
        """Не принимает отказ авторизации с HTTP 200 за успешную проверку."""
        p = InstalledPlatforms(FixtureHttp([{"success": False}])).get("rozetka")
        v = p.validate(
            ConnectionConfigVO.create(
                version=1,
                endpoint="https://api-seller.rozetka.com.ua",
                settings={},
            ),
            {"token": "secret"},
        )
        with self.assertRaises(VerificationFailure) as error:
            await p.verify(v.config, v.credentials)
        self.assertEqual(error.exception.code, "invalid_credentials")

    async def test_missing_models_and_unsafe_urls_are_rejected(self) -> None:
        """Отклоняет неполные credentials, неизвестную платформу и небезопасные URL."""
        registry = InstalledPlatforms()
        for url in (
            "http://shop.example",
            "https://127.0.0.1",
            "https://[::1]",
            "https://user:secret@shop.example",
            "https://shop.example?key=secret",
            "https://localhost",
        ):
            with self.assertRaises(ChannelInputError):
                registry.get("woocommerce").validate(
                    ConnectionConfigVO.create(version=1, endpoint=url, settings={}),
                    {"consumer_key": "ck", "consumer_secret": "cs"},
                )
        for credentials in (
            {},
            {"token": ""},
            {"token": "secret", "unknown": "secret"},
        ):
            with self.assertRaises(ChannelInputError) as error:
                registry.get("prom").validate(
                    ConnectionConfigVO.create(
                        version=1, endpoint="https://my.prom.ua", settings={}
                    ),
                    credentials,
                )
            self.assertNotIn("secret", str(error.exception))
        with self.assertRaises(ChannelInputError):
            registry.get("unknown")
        with self.assertRaises(ChannelInputError):
            registry.get("prom").validate(
                ConnectionConfigVO.create(
                    version=2, endpoint="https://my.prom.ua", settings={}
                ),
                {"token": "secret"},
            )

    async def test_transport_rejects_mixed_dns_before_sending_credentials(self) -> None:
        """Запрещает смешанные публичные и приватные ответы DNS до отправки секрета."""
        answers = [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ]
        with (
            patch.object(
                asyncio.get_running_loop(),
                "getaddrinfo",
                AsyncMock(return_value=answers),
            ),
            patch.object(
                httpx.AsyncHTTPTransport, "handle_async_request", AsyncMock()
            ) as send,
        ):
            with self.assertRaises(VerificationFailure):
                await PublicHttpsTransport().handle_async_request(
                    httpx.Request(
                        "GET",
                        "https://shop.example",
                        headers={"Authorization": "Basic secret"},
                    )
                )
            send.assert_not_called()

    async def test_transport_maps_statuses_without_response_body(self) -> None:
        """Отображает HTTP-отказы в безопасные коды с правильной политикой повтора."""
        for status, code, retryable in [
            (401, "invalid_credentials", False),
            (403, "permission_missing", False),
            (429, "rate_limited", True),
            (503, "provider_unavailable", True),
            (302, "endpoint_redirected", False),
        ]:

            async def response(request: httpx.Request) -> httpx.Response:
                """Возвращает HTTP-статус и искусственное тело для проверки отображения ошибок."""
                return httpx.Response(
                    status, content=b"secret-provider-body", request=request
                )

            with patch(
                "src.modules.channels.infrastructure.http.PublicHttpsTransport",
                lambda: httpx.MockTransport(response),
            ):
                with self.assertRaises(VerificationFailure) as error:
                    await SafeJsonHttp().request("GET", "https://shop.example")
                self.assertEqual(
                    (error.exception.code, error.exception.retryable), (code, retryable)
                )
                self.assertNotIn("secret", str(error.exception))


class ChannelStateTests(unittest.TestCase):
    """Проверяет поколения конфигурации и закрепление identity."""

    def setUp(self) -> None:
        """Создаёт исходный агрегат и детерминированный контекст проверки."""
        self.now = datetime.now(UTC)
        self.actor, self.job_id = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.config = ConnectionConfigVO.create(
            version=1, endpoint="https://my.prom.ua", settings={}
        )
        self.channel = Channel.create(
            channel_id=EntityIdVO(uuid4()),
            name=ChannelNameVO(" Shop "),
            platform_kind="prom",
            connection=Connection.create(
                connection_id=EntityIdVO(uuid4()),
                config=self.config,
                encrypted_credentials=b"encrypted",
                job_id=self.job_id,
                now=self.now,
            ),
            actor_id=self.actor,
            now=self.now,
        )

    def test_revision_and_identity_are_independent_of_renaming(self) -> None:
        """Сохраняет актуальность проверки при изменении только названия."""
        self.assertFalse(
            self.channel.change_settings(
                expected_revision=1,
                name=ChannelNameVO("Renamed"),
                config=None,
                encrypted_credentials=None,
                job_id=EntityIdVO(uuid4()),
                actor_id=self.actor,
                now=self.now,
            )
        )
        self.channel.apply_verification(
            job_id=self.job_id,
            config_revision=1,
            identity=ResourceIdentityVO(namespace="prom.root_group", key="1"),
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel.connection.verification.status, "verified")
        self.assertEqual(self.channel.connection.config_revision, 1)
        with self.assertRaises(ChannelRevisionConflictError):
            self.channel.require_revision(1)

    def test_replacement_and_late_result_cannot_switch_identity(self) -> None:
        """Отсекает старый результат и запрещает подмену закреплённого магазина."""
        identity = ResourceIdentityVO(namespace="prom.root_group", key="1")
        self.channel.apply_verification(
            job_id=self.job_id,
            config_revision=1,
            identity=identity,
            error_code=None,
            now=self.now,
        )
        new_job = EntityIdVO(uuid4())
        self.channel.change_settings(
            expected_revision=self.channel.revision,
            name=None,
            config=None,
            encrypted_credentials=b"new-secret",
            job_id=new_job,
            actor_id=self.actor,
            now=self.now,
        )
        self.assertEqual(self.channel.connection.encrypted_credentials, b"new-secret")
        self.assertEqual(self.channel.connection.verification.status, "pending")
        self.channel.apply_verification(
            job_id=self.job_id,
            config_revision=1,
            identity=ResourceIdentityVO(namespace="prom.root_group", key="2"),
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel.connection.verification.status, "pending")
        self.channel.apply_verification(
            job_id=new_job,
            config_revision=2,
            identity=ResourceIdentityVO(namespace="prom.root_group", key="2"),
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel.connection.identity, identity)
        self.assertEqual(
            self.channel.connection.verification.error_code, "resource_identity_changed"
        )

    def test_cipher_and_absent_credentials_semantics(self) -> None:
        """Проверяет шифрование и различие пропущенных credentials и null."""
        cipher = FernetCipher(Fernet.generate_key().decode())
        ciphertext = cipher.encrypt(b"secret")
        self.assertNotIn(b"secret", ciphertext)
        self.assertEqual(cipher.decrypt(ciphertext), b"secret")
        with self.assertRaises(CipherNotConfigured):
            FernetCipher(None).encrypt(b"secret")
        with self.assertRaises(CiphertextUnreadable):
            FernetCipher(Fernet.generate_key().decode()).decrypt(ciphertext)
        self.assertIsNone(
            UpdateChannelRequest(expected_revision=1, name="Name").credentials
        )
        with self.assertRaises(ValidationError):
            UpdateChannelRequest(expected_revision=1, credentials=None)


class ChannelErrorContractTests(unittest.TestCase):
    """Сохраняет публичное отображение ошибок после разделения слоёв."""

    def test_domain_and_platform_errors_keep_public_codes(self) -> None:
        """Presentation добавляет к предметным ошибкам прежние коды и поля формы."""
        for error, status, code, field in (
            (ChannelNotFoundError(), 404, "channel_not_found", None),
            (ChannelRevisionConflictError(), 409, "revision_conflict", None),
            (InvalidChannelNameError(), 422, "name_invalid", "name"),
            (InvalidChannelStateError(), 422, "stored_channel_invalid", None),
            (
                InvalidResourceIdentityError(),
                422,
                "resource_identity_unavailable",
                None,
            ),
            (
                ChannelInputError("credentials_invalid", field="credentials.token"),
                422,
                "credentials_invalid",
                "credentials.token",
            ),
        ):
            with self.subTest(code=code):
                result = channel_http_error(error)
                self.assertEqual(result.status_code, status)
                self.assertEqual(result.detail, {"code": code, "field": field})
