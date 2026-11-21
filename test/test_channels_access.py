"""Проверка Application-сценария доступа без SQL и транспорта worker."""

import asyncio
from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock

from src.modules.channels.application.command.check_connection_access.command import (
    CheckConnectionAccessCommand,
)
from src.modules.channels.application.command.check_connection_access.handler import (
    CheckConnectionAccessHandler,
)
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.port.platform import Platform, PlatformRegistry
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from test import test_channels as support


class CheckConnectionAccessTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет окончательные отказы, повторы и отсутствие секретов в результате."""

    def setUp(self) -> None:
        """Собирает сценарий только из подменяемых Application-портов."""
        self.cipher = Mock(spec=Cipher)
        self.cipher.decrypt.return_value = b"plaintext-secret"
        self.platform = Mock(spec=Platform)
        self.identity = ResourceIdentityVO(namespace="prom.root_group", key="7")
        self.platform.verify = AsyncMock(return_value=self.identity)
        registry = Mock(spec=PlatformRegistry)
        registry.get.return_value = self.platform
        self.handler = CheckConnectionAccessHandler(
            platforms=registry, cipher=self.cipher
        )
        self.command = CheckConnectionAccessCommand(
            platform_kind="prom",
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://my.prom.ua", settings={}
            ),
            encrypted_credentials=b"encrypted",
            attempt=1,
            max_attempts=3,
        )

    async def test_success_returns_only_identity(self) -> None:
        """Секрет остаётся аргументом порта и не возвращается вызывающему worker."""
        result = await self.handler.execute(self.command)
        self.assertEqual(result.identity, self.identity)
        self.assertIsNone(result.error_code)
        self.assertNotIn("secret", repr(result))
        self.assertNotIn("encrypted", repr(self.command))
        self.platform.verify.assert_awaited_once_with(
            self.command.config, b"plaintext-secret"
        )

    async def test_retryable_failures_are_final_only_on_last_attempt(self) -> None:
        """Временный отказ и timeout повторяются до установленного лимита."""
        for error, code in (
            (VerificationFailure("rate_limited", retryable=True), "rate_limited"),
            (TimeoutError(), "network_timeout"),
        ):
            with self.subTest(code=code):
                self.platform.verify.side_effect = error
                with self.assertRaises(VerificationFailure) as failure:
                    await self.handler.execute(self.command)
                self.assertTrue(failure.exception.retryable)
                result = await self.handler.execute(replace(self.command, attempt=3))
                self.assertEqual(result.error_code, code)
                self.assertIsNone(result.identity)

    async def test_credentials_errors_do_not_call_platform(self) -> None:
        """Отсутствующий ключ откладывает задание, нечитаемый секрет даёт безопасный отказ."""
        self.cipher.decrypt.side_effect = CipherNotConfigured()
        with self.assertRaises(ScheduledJobDeferred):
            await self.handler.execute(self.command)
        self.cipher.decrypt.side_effect = CiphertextUnreadable()
        result = await self.handler.execute(self.command)
        self.assertEqual(result.error_code, "credentials_unreadable")
        self.platform.verify.assert_not_awaited()

    async def test_terminal_failure_and_unexpected_errors_are_distinct(self) -> None:
        """Предсказуемый отказ становится результатом, ошибка реализации не маскируется."""
        self.platform.verify.side_effect = VerificationFailure("invalid_credentials")
        self.assertEqual(
            (await self.handler.execute(self.command)).error_code, "invalid_credentials"
        )
        self.platform.verify.side_effect = ValueError("programming error")
        with self.assertRaises(ValueError):
            await self.handler.execute(self.command)
        self.platform.verify.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.handler.execute(self.command)

    async def test_packages_hide_validation_errors_from_malformed_responses(
        self,
    ) -> None:
        """Конкретный пакет переводит ошибки Pydantic в безопасный контракт порта."""
        for kind, endpoint, credentials in (
            ("prom", "https://my.prom.ua", {"token": "secret"}),
            ("rozetka", "https://api-seller.rozetka.com.ua", {"token": "secret"}),
            (
                "woocommerce",
                "https://shop.example",
                {"consumer_key": "ck", "consumer_secret": "cs"},
            ),
        ):
            with self.subTest(kind=kind):
                platform = InstalledPlatforms(
                    support.FixtureHttp([{"secret-payload": "never expose"}])
                ).get(kind)
                config = platform.validate_config(
                    ConnectionConfigVO.create(version=1, endpoint=endpoint, settings={})
                ).config
                with self.assertRaises(VerificationFailure) as failure:
                    await platform.verify(
                        config, platform.encode_credentials(credentials)
                    )
                self.assertEqual(failure.exception.code, "provider_response_invalid")
                self.assertIsNone(failure.exception.__cause__)
                self.assertNotIn("secret", str(failure.exception))
