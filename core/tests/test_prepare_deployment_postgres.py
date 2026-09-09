"""Exercise deployment concurrency against disposable PostgreSQL databases."""

import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

CORE_DIR = Path(__file__).resolve().parents[1]
POSTGRES_URL = os.environ.get("TEST_CORE_POSTGRES_URL")
MIGRATION_LOCK_ID = int.from_bytes(b"dnk:core", "big")


@unittest.skipUnless(
    POSTGRES_URL, "Set TEST_CORE_POSTGRES_URL with CREATEDB privileges"
)
class PrepareDeploymentPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = psycopg.connect(POSTGRES_URL, autocommit=True)
        cls.addClassCleanup(cls.admin.close)

    def setUp(self):
        self.database = "dnk_prepare_test_" + uuid4().hex
        self.admin.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database))
        )
        self.addCleanup(self.drop_database)
        self.dsn = make_conninfo(POSTGRES_URL, dbname=self.database)
        self.db = psycopg.connect(self.dsn, autocommit=True)
        self.addCleanup(self.db.close)
        params = conninfo_to_dict(POSTGRES_URL)
        self.environment = {
            **{
                key: value
                for key, value in os.environ.items()
                if not key.startswith("CORE_")
            },
            "PYTHONPATH": str(CORE_DIR / "src"),
            "DJANGO_SETTINGS_MODULE": "dnk_core.settings",
            "PGAPPNAME": self.database,
            "CORE_ENV_FILE": "",
            "CORE_DEBUG": "true",
            "CORE_SECRET_KEY": "temporary-preparation-integration-test-key",
            "CORE_DB_NAME": self.database,
            "CORE_DB_USER": self.admin.info.user,
            "CORE_DB_PASSWORD": params.get("password", ""),
            "CORE_DB_HOST": self.admin.info.host,
            "CORE_DB_PORT": str(self.admin.info.port),
        }

    def drop_database(self):
        self.admin.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                sql.Identifier(self.database)
            )
        )

    def start_command(self, wait_timeout=30, code=None):
        arguments = [sys.executable]
        if code:
            arguments += ["-c", code]
        else:
            arguments += [
                str(CORE_DIR / "src" / "manage.py"),
                "prepare_deployment",
                "--wait-timeout",
                str(wait_timeout),
                "--verbosity",
                "0",
            ]
        process = subprocess.Popen(
            arguments,
            cwd=CORE_DIR,
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop_command, process)
        return process

    @staticmethod
    def stop_command(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)

    def finish_command(self, process, succeeds=True):
        stdout, stderr = process.communicate(timeout=45)
        if succeeds:
            self.assertEqual(process.returncode, 0, stdout + stderr)
        else:
            self.assertNotEqual(process.returncode, 0, stdout + stderr)
        return stdout + stderr

    def wait_for_sessions(self, count=1, query=None):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            sessions = self.admin.execute(
                "SELECT pid, query FROM pg_stat_activity "
                "WHERE datname = %s AND application_name = %s",
                [self.database, self.database],
            ).fetchall()
            if len(sessions) == count and (query is None or sessions[0][1] == query):
                return sessions
            time.sleep(0.05)
        self.fail("Deployment processes did not reach the expected database operation.")

    def test_parallel_startup_and_repeated_migration_preserve_other_schemas(self):
        original_path = self.db.execute("SHOW search_path").fetchone()
        self.db.execute("CREATE TABLE public.django_migrations (marker text)")
        self.db.execute(
            "INSERT INTO public.django_migrations VALUES ('runtime history')"
        )
        self.db.execute("CREATE SCHEMA tenant_probe")
        self.db.execute("CREATE TABLE tenant_probe.inventory (marker text)")
        self.db.execute("INSERT INTO tenant_probe.inventory VALUES ('tenant data')")
        self.db.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_ID])

        processes = [self.start_command() for _ in range(3)]
        self.wait_for_sessions(count=3)
        self.assertIsNone(
            self.db.execute("SELECT to_regnamespace('core')").fetchone()[0]
        )
        self.db.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])
        for process in processes:
            self.finish_command(process)

        history = self.db.execute(
            "SELECT app, name, applied FROM core.django_migrations ORDER BY id"
        ).fetchall()
        self.assertTrue(history)
        self.assertEqual(len(history), len({(app, name) for app, name, _ in history}))
        self.finish_command(self.start_command())
        self.assertEqual(
            history,
            self.db.execute(
                "SELECT app, name, applied FROM core.django_migrations ORDER BY id"
            ).fetchall(),
        )
        self.assertEqual(
            self.db.execute("SELECT * FROM public.django_migrations").fetchall(),
            [("runtime history",)],
        )
        self.assertEqual(
            self.db.execute("SELECT * FROM tenant_probe.inventory").fetchall(),
            [("tenant data",)],
        )
        self.assertEqual(self.db.execute("SHOW search_path").fetchone(), original_path)
        with psycopg.connect(self.dsn) as fresh:
            self.assertEqual(
                fresh.execute("SHOW search_path").fetchone(), original_path
            )

    def test_lock_timeout_leaves_schema_untouched_and_later_retry_succeeds(self):
        self.db.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_ID])
        started = time.monotonic()
        output = self.finish_command(self.start_command(wait_timeout=2), succeeds=False)
        self.assertIn("Timed out waiting for the Core migration lock", output)
        self.assertLess(time.monotonic() - started, 15)
        self.assertIsNone(
            self.db.execute("SELECT to_regnamespace('core')").fetchone()[0]
        )
        self.db.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])
        self.finish_command(self.start_command())

    def test_connection_loss_cannot_resume_migrations_on_an_unlocked_session(self):
        code = """
import django
django.setup()
from django.core.management import call_command
from django.db import connection, DatabaseError
from accounts.management.commands import prepare_deployment

original_migrate = prepare_deployment.call_command
def interrupted_migrate(*args, **kwargs):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(30)")
    except DatabaseError:
        connection.close()
    original_migrate(*args, **kwargs)

prepare_deployment.call_command = interrupted_migrate
call_command("prepare_deployment", wait_timeout=30, verbosity=0)
"""
        process = self.start_command(code=code)
        [(pid, _)] = self.wait_for_sessions(query="SELECT pg_sleep(30)")
        self.admin.execute("SELECT pg_terminate_backend(%s)", [pid])
        output = self.finish_command(process, succeeds=False)
        self.assertIn("session was lost", output)
        self.assertIsNone(
            self.db.execute("SELECT to_regclass('core.django_migrations')").fetchone()[
                0
            ]
        )
        self.finish_command(self.start_command())

    def test_migration_error_releases_lock_and_can_be_retried_after_repair(self):
        self.db.execute("CREATE SCHEMA core")
        self.db.execute("CREATE TABLE core.django_migrations (invalid_column text)")
        output = self.finish_command(self.start_command(), succeeds=False)
        self.assertIn("Core database preparation failed (ProgrammingError)", output)
        self.assertTrue(
            self.db.execute(
                "SELECT pg_try_advisory_lock(%s)", [MIGRATION_LOCK_ID]
            ).fetchone()[0]
        )
        self.db.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])
        # Repair only our deliberately malformed fixture in this disposable DB.
        self.db.execute("DROP TABLE core.django_migrations")
        self.finish_command(self.start_command())


if __name__ == "__main__":
    unittest.main()
