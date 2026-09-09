"""Failure and timeout coverage for serialized deployment preparation."""

from io import StringIO
import unittest
from unittest.mock import Mock, patch

import psycopg
from django.core.management.base import CommandError
from django.db import OperationalError

from accounts.management.commands import prepare_deployment as preparation


class Clock:
    def __init__(self):
        self.now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Cursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, parameters=None):
        self.connection.statements.append((statement, parameters))
        if self.connection.statement_error:
            raise self.connection.statement_error

    def fetchone(self):
        return (self.connection.lock_available(),)


class Session:
    def __init__(self, connection):
        self.wrapper = connection
        self.closed = False

    def cursor(self):
        return Cursor(self.wrapper)


class Connection:
    vendor = "postgresql"
    in_atomic_block = False
    Database = psycopg

    def __init__(self):
        self.settings_dict = {
            "OPTIONS": {"options": "-c search_path=core", "sslmode": "verify-full"},
            "AUTOCOMMIT": True,
        }
        self.connection = None
        self.statements = []
        self.statement_error = None
        self.connect_options = []
        self.connection_failure = Mock(return_value=None)
        self.lock_available = Mock(return_value=True)

    def connect(self):
        self.connect_options.append(self.settings_dict["OPTIONS"].copy())
        self.connection_failure()
        self.connection = Session(self)

    def ensure_connection(self):
        if self.connection is None:
            self.connect()

    def cursor(self):
        self.ensure_connection()
        return self.connection.cursor()

    def close(self):
        if self.connection is not None:
            self.connection.closed = True
            self.connection = None


class PrepareDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.connection = Connection()
        self.original_options = self.connection.settings_dict["OPTIONS"]
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.command = preparation.Command(stdout=self.stdout, stderr=self.stderr)
        self.migrate = self.enterContext(patch.object(preparation, "call_command"))
        self.enterContext(
            patch.object(preparation, "connections", {"default": self.connection})
        )
        self.enterContext(
            patch.object(preparation.time, "monotonic", self.clock.monotonic)
        )
        self.enterContext(patch.object(preparation.time, "sleep", self.clock.sleep))

    def run_preparation(self, timeout=5):
        self.command.handle(wait_timeout=timeout, verbosity=0)

    def statements(self):
        return [statement for statement, _ in self.connection.statements]

    def test_migrations_share_lock_session_and_keep_normal_transactions(self):
        sessions = []

        def migrate(*args, **kwargs):
            sessions.append(self.connection.connection)
            self.assertFalse(self.connection.in_atomic_block)
            self.assertTrue(self.connection.settings_dict["AUTOCOMMIT"])
            self.assertEqual(
                self.statements()[-1], 'CREATE SCHEMA IF NOT EXISTS "core"'
            )

        self.migrate.side_effect = migrate
        self.run_preparation()
        self.migrate.assert_called_once_with(
            "migrate",
            database="default",
            interactive=False,
            verbosity=0,
            stdout=self.command.stdout,
            stderr=self.command.stderr,
        )
        self.assertEqual(
            self.statements(),
            [
                "SELECT pg_try_advisory_lock(%s)",
                'CREATE SCHEMA IF NOT EXISTS "core"',
                "SELECT pg_advisory_unlock(%s)",
            ],
        )
        self.assertEqual(len(self.connection.connect_options), 1)
        self.assertTrue(sessions[0].closed)
        self.assertIs(self.connection.settings_dict["OPTIONS"], self.original_options)

    def test_failed_connections_retry_with_bounded_connect_timeout(self):
        self.connection.connection_failure.side_effect = [
            OperationalError("secret"),
            None,
        ]
        self.run_preparation(timeout=300)
        self.assertEqual(len(self.connection.connect_options), 2)
        for options in self.connection.connect_options:
            self.assertEqual(options, {**self.original_options, "connect_timeout": 5})
        self.assertEqual(self.clock.now, 1)
        self.assertNotIn("secret", self.stderr.getvalue())

    def test_connection_wait_expires_without_running_migrations_or_logging_credentials(
        self,
    ):
        self.connection.connection_failure.side_effect = OperationalError(
            "password=hunter2"
        )
        with self.assertRaisesRegex(
            CommandError, "Timed out waiting.*PostgreSQL"
        ) as error:
            self.run_preparation()
        self.assertNotIn("hunter2", str(error.exception) + self.stderr.getvalue())
        self.assertEqual(self.clock.now, 5)
        self.migrate.assert_not_called()
        self.assertIs(self.connection.settings_dict["OPTIONS"], self.original_options)

    def test_contended_lock_is_polled_on_same_session(self):
        self.connection.lock_available.side_effect = [False, False, True]
        self.run_preparation()
        self.assertEqual(self.clock.now, 2)
        self.assertEqual(len(self.connection.connect_options), 1)
        self.migrate.assert_called_once()

    def test_lock_wait_expires_without_creating_schema(self):
        self.connection.lock_available.return_value = False
        with self.assertRaisesRegex(CommandError, "Timed out waiting.*migration lock"):
            self.run_preparation()
        self.assertEqual(self.clock.now, 5)
        self.assertEqual(set(self.statements()), {"SELECT pg_try_advisory_lock(%s)"})
        self.migrate.assert_not_called()
        self.assertIsNone(self.connection.connection)

    def test_failed_lock_query_is_terminal_and_does_not_reconnect(self):
        self.connection.statement_error = OperationalError("password=hunter2")
        with self.assertRaisesRegex(CommandError, "failed.*OperationalError") as error:
            self.run_preparation()
        self.assertNotIn("hunter2", str(error.exception))
        self.assertEqual(len(self.connection.connect_options), 1)
        self.migrate.assert_not_called()

    def test_failed_migration_unlocks_and_redacts_exception_details(self):
        self.migrate.side_effect = RuntimeError("sensitive row data")
        with self.assertRaisesRegex(CommandError, "failed.*RuntimeError") as error:
            self.run_preparation()
        self.assertNotIn("sensitive", str(error.exception))
        self.assertEqual(self.statements()[-1], "SELECT pg_advisory_unlock(%s)")
        self.assertIsNone(self.connection.connection)

    def test_migration_cannot_reconnect_after_losing_locked_session(self):
        def reconnect(*args, **kwargs):
            self.connection.close()
            self.connection.ensure_connection()

        self.migrate.side_effect = reconnect
        with self.assertRaisesRegex(CommandError, "session was lost"):
            self.run_preparation()
        self.assertEqual(len(self.connection.connect_options), 1)
        self.assertNotIn("SELECT pg_advisory_unlock(%s)", self.statements())
        # The guard is removed when the command returns.
        self.connection.ensure_connection()
        self.assertEqual(len(self.connection.connect_options), 2)
        self.connection.close()

    def test_session_loss_without_another_query_still_fails(self):
        self.migrate.side_effect = lambda *args, **kwargs: self.connection.close()
        with self.assertRaisesRegex(CommandError, "session was lost"):
            self.run_preparation()
        self.assertEqual(len(self.connection.connect_options), 1)

    def test_invalid_execution_context_is_rejected_before_connecting(self):
        for attribute, value, message in (
            ("vendor", "sqlite", "requires PostgreSQL"),
            ("in_atomic_block", True, "autocommit"),
        ):
            with self.subTest(attribute=attribute):
                with patch.object(self.connection, attribute, value):
                    with self.assertRaisesRegex(CommandError, message):
                        self.run_preparation()
        with self.assertRaisesRegex(CommandError, "at least 2"):
            self.run_preparation(timeout=1)
        self.connection.settings_dict["OPTIONS"]["pool"] = True
        with self.assertRaisesRegex(CommandError, "unpooled"):
            self.run_preparation()
        self.assertEqual(self.connection.connect_options, [])


if __name__ == "__main__":
    unittest.main()
