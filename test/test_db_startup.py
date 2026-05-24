from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import src.app_factory as app_factory
import src.modules.shared.infrastructure.persistence.database_helper as db_helper_module
from src.dnk_app import DnkApp
from src.modules.shared.infrastructure.persistence.database_helper import (
    DatabaseHelper,
    DatabaseStartupError,
)


class DatabaseStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_for_startup_succeeds_on_first_attempt(self) -> None:
        helper = DatabaseHelper()
        create_all_mock = AsyncMock(return_value=None)

        with (
            patch.object(helper, "create_all", create_all_mock),
            patch(
                "src.modules.shared.infrastructure.persistence.database_helper.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep_mock,
            patch.object(db_helper_module.dnk_config, "DB_STARTUP_MAX_ATTEMPTS", 5),
            patch.object(
                db_helper_module.dnk_config,
                "DB_STARTUP_RETRY_DELAY_SECONDS",
                1,
            ),
        ):
            await helper.initialize_for_startup()

        self.assertEqual(create_all_mock.await_count, 1)
        sleep_mock.assert_not_awaited()

    async def test_initialize_for_startup_retries_and_then_succeeds(self) -> None:
        helper = DatabaseHelper()
        create_all_mock = AsyncMock(
            side_effect=[OSError("down-1"), OSError("down-2"), None]
        )

        with (
            patch.object(helper, "create_all", create_all_mock),
            patch(
                "src.modules.shared.infrastructure.persistence.database_helper.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep_mock,
            patch.object(db_helper_module.dnk_config, "DB_STARTUP_MAX_ATTEMPTS", 5),
            patch.object(
                db_helper_module.dnk_config,
                "DB_STARTUP_RETRY_DELAY_SECONDS",
                1,
            ),
        ):
            await helper.initialize_for_startup()

        self.assertEqual(create_all_mock.await_count, 3)
        self.assertEqual(sleep_mock.await_count, 2)

    async def test_initialize_for_startup_raises_database_startup_error_after_retries(
        self,
    ) -> None:
        helper = DatabaseHelper()
        create_all_mock = AsyncMock(side_effect=OSError("connection refused"))

        with (
            patch.object(helper, "create_all", create_all_mock),
            patch(
                "src.modules.shared.infrastructure.persistence.database_helper.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep_mock,
            patch.object(db_helper_module.dnk_config, "DB_STARTUP_MAX_ATTEMPTS", 3),
            patch.object(
                db_helper_module.dnk_config,
                "DB_STARTUP_RETRY_DELAY_SECONDS",
                0,
            ),
            patch.object(db_helper_module.dnk_config, "DB_HOST", "db.example.local"),
            patch.object(db_helper_module.dnk_config, "DB_PORT", 5432),
            patch.object(db_helper_module.dnk_config, "DB_DATABASE", "dnk"),
        ):
            with self.assertRaises(DatabaseStartupError) as caught:
                await helper.initialize_for_startup()

        self.assertIn("Database startup failed after 3 attempts", str(caught.exception))
        self.assertIn("host=db.example.local", str(caught.exception))
        self.assertIn("port=5432", str(caught.exception))
        self.assertIn("database=dnk", str(caught.exception))
        self.assertIn("retry_delay=0s", str(caught.exception))
        self.assertEqual(create_all_mock.await_count, 3)
        self.assertEqual(sleep_mock.await_count, 2)

    async def test_initialize_for_startup_does_not_retry_non_retryable_error(
        self,
    ) -> None:
        helper = DatabaseHelper()
        create_all_mock = AsyncMock(side_effect=RuntimeError("unexpected failure"))

        with (
            patch.object(helper, "create_all", create_all_mock),
            patch(
                "src.modules.shared.infrastructure.persistence.database_helper.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep_mock,
            patch.object(db_helper_module.dnk_config, "DB_STARTUP_MAX_ATTEMPTS", 5),
            patch.object(
                db_helper_module.dnk_config,
                "DB_STARTUP_RETRY_DELAY_SECONDS",
                1,
            ),
        ):
            with self.assertRaises(RuntimeError):
                await helper.initialize_for_startup()

        self.assertEqual(create_all_mock.await_count, 1)
        sleep_mock.assert_not_awaited()

    async def test_lifespan_disposes_engine_when_startup_fails(self) -> None:
        startup_error = RuntimeError("database is unavailable")
        helper_stub = type(
            "HelperStub",
            (),
            {
                "session_factory": object(),
                "initialize_for_startup": AsyncMock(side_effect=startup_error),
                "dispose": AsyncMock(return_value=None),
            },
        )()
        app = DnkApp()

        with patch.object(app_factory, "db_helper", helper_stub):
            with self.assertRaises(RuntimeError) as caught:
                async with app_factory.lifespan(app):
                    self.fail("lifespan context should not yield on startup failure")

        self.assertIs(caught.exception, startup_error)
        self.assertIs(app.state.db, helper_stub.session_factory)
        self.assertIs(app.state.db_helper, helper_stub)
        helper_stub.initialize_for_startup.assert_awaited_once()
        helper_stub.dispose.assert_awaited_once()
