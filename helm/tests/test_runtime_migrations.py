"""Readiness failures must never turn into retried migration transactions."""

import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path
import unittest
from unittest.mock import AsyncMock

SCRIPT = Path(__file__).resolve().parents[1] / "dnk-runtime-core/files/migrate.py"
spec = importlib.util.spec_from_file_location("runtime_migrations", SCRIPT)
migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrations)


class Connection:
    def __init__(self, lock=True):
        self.committed = False
        self.rolled_back = False
        self.scalar = AsyncMock(return_value=lock)
        self.execute = AsyncMock()
        self.close = AsyncMock()

    @asynccontextmanager
    async def begin(self):
        try:
            yield self
        except BaseException:
            self.rolled_back = True
            raise
        else:
            self.committed = True


class Engine:
    def __init__(self, connection=None, error=None):
        self.connect = AsyncMock(return_value=connection, side_effect=error)


class RuntimeMigrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_callbacks_and_order_share_transaction_connection(self):
        connection = Connection()
        engine = Engine(connection)
        calls = []

        async def bootstrap(conn):
            self.assertIs(conn, connection)
            calls.append("bootstrap")

        async def ids(conn):
            self.assertIs(conn, connection)
            calls.append("ids")
            return ["first", "second"]

        async def upgrade(conn, tenant):
            self.assertIs(conn, connection)
            self.assertFalse(conn.committed)
            calls.append(tenant)

        await migrations.prepare(engine, bootstrap, ids, upgrade)
        self.assertEqual(calls, ["bootstrap", "ids", "first", "second"])
        self.assertTrue(connection.committed)
        engine.connect.assert_awaited_once()
        connection.close.assert_awaited_once()

    async def test_failure_aborts_batch_without_reconnecting(self):
        connection = Connection()
        engine = Engine(connection)
        upgrade = AsyncMock(side_effect=[None, ConnectionError("connection lost")])
        with self.assertRaises(ConnectionError):
            await migrations.prepare(
                engine, AsyncMock(), AsyncMock(return_value=[1, 2, 3]), upgrade
            )
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertEqual(upgrade.await_count, 2)
        engine.connect.assert_awaited_once()
        connection.close.assert_awaited_once()

    async def test_lock_timeout_prevents_any_bootstrap(self):
        connection = Connection(lock=False)
        bootstrap = AsyncMock()
        with self.assertRaises(TimeoutError):
            await migrations.prepare(
                Engine(connection),
                bootstrap,
                AsyncMock(),
                AsyncMock(),
                wait_timeout=0.01,
            )
        bootstrap.assert_not_awaited()
        self.assertTrue(connection.rolled_back)
        connection.close.assert_awaited_once()

    async def test_unavailable_database_expires_without_bootstrap(self):
        bootstrap = AsyncMock()
        with self.assertRaises(TimeoutError):
            await migrations.prepare(
                Engine(error=ConnectionRefusedError()),
                bootstrap,
                AsyncMock(),
                AsyncMock(),
                wait_timeout=0.01,
            )
        bootstrap.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
