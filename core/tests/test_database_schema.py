"""PostgreSQL regression check using a newly created, disposable database."""

import os
import base64
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

CORE_DIR = Path(__file__).resolve().parents[1]
POSTGRES_URL = os.environ.get("TEST_CORE_POSTGRES_URL")


@unittest.skipUnless(
    POSTGRES_URL, "Set TEST_CORE_POSTGRES_URL with CREATEDB privileges"
)
class CoreSchemaTests(unittest.TestCase):
    """Verify CORE migrations are isolated inside a disposable PostgreSQL database."""

    @classmethod
    def setUpClass(cls):
        """Create a fresh database and disable all deployment dotenv sources."""
        cls.admin = psycopg.connect(POSTGRES_URL, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        cls.database = "dnk_core_test_" + uuid4().hex
        cls.admin.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database))
        )
        cls.addClassCleanup(cls.drop_database)
        cls.dsn = make_conninfo(POSTGRES_URL, dbname=cls.database)
        params = conninfo_to_dict(POSTGRES_URL)
        cls.environment = {
            **{
                key: value
                for key, value in os.environ.items()
                if not key.startswith("CORE_")
            },
            "CORE_ENV_FILE": "",
            "DJANGO_SETTINGS_MODULE": "dnk_core.settings",
            "CORE_SECRET_KEY": "temporary-schema-integration-test-key",
            "CORE_DEBUG": "true",
            "CORE_DB_NAME": cls.database,
            "CORE_DB_USER": cls.admin.info.user,
            "CORE_DB_PASSWORD": params.get("password", ""),
            "CORE_DB_HOST": cls.admin.info.host,
            "CORE_DB_PORT": str(cls.admin.info.port),
        }

    @classmethod
    def drop_database(cls):
        """Drop only the uniquely named database created by this test class."""
        cls.admin.execute(
            sql.SQL("DROP DATABASE {}").format(sql.Identifier(cls.database))
        )

    def run_command(self, script, *arguments, succeeds=True, environment=None):
        """Execute a Django command against the disposable CORE configuration."""
        result = subprocess.run(
            [sys.executable, str(CORE_DIR / "src" / script), *arguments],
            cwd=CORE_DIR,
            env=environment or self.environment,
            capture_output=True,
            text=True,
        )
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_existing_runtime_data_and_migration_history_are_untouched(self):
        """Repeated migrations preserve public/tenant data and refuse scaffold resets."""
        with psycopg.connect(self.dsn, autocommit=True) as database:
            original_path = database.execute("SHOW search_path").fetchone()
            database.execute("CREATE TABLE public.auth_user (marker text)")
            database.execute("INSERT INTO public.auth_user VALUES ('runtime user')")
            database.execute("CREATE TABLE public.django_migrations (marker text)")
            database.execute(
                "INSERT INTO public.django_migrations VALUES ('runtime history')"
            )
            database.execute("CREATE SCHEMA tenant_probe")
            database.execute("CREATE TABLE tenant_probe.inventory (marker text)")
            database.execute(
                "INSERT INTO tenant_probe.inventory VALUES ('tenant data')"
            )

            missing = self.run_command(
                "manage.py", "migrate", "--noinput", succeeds=False
            )
            self.assertIn("no schema has been selected", missing.stderr)

            database.execute("CREATE SCHEMA core")
            database.execute("CREATE TABLE core.auth_user (marker text)")
            database.execute("INSERT INTO core.auth_user VALUES ('temporary user')")
            production = {
                **self.environment,
                "CORE_DEBUG": "false",
                "CORE_PUBLIC_ORIGIN": "https://example.com",
                "CORE_ALLOWED_HOSTS": "example.com",
                "CORE_MFA_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"x" * 32).decode(),
                "CORE_REDIS_URL": "redis://127.0.0.1:6379/2",
            }
            refused = self.run_command(
                "prepare_database.py",
                "--reset-scaffold",
                succeeds=False,
                environment=production,
            )
            self.assertIn("requires CORE_DEBUG=true", refused.stderr)
            self.assertEqual(
                database.execute("SELECT COUNT(*) FROM core.auth_user").fetchone(),
                (1,),
            )
            self.run_command("prepare_database.py", "--reset-scaffold")
            self.assertEqual(
                database.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'core'"
                ).fetchall(),
                [],
            )
            self.run_command("prepare_database.py")
            self.run_command("manage.py", "migrate", "accounts", "0001", "--noinput")
            legacy_id = uuid4()
            database.execute(
                "INSERT INTO core.accounts_user "
                "(id, username, email, password, first_name, last_name, is_staff, "
                "is_superuser, is_active, date_joined, phone_verified) "
                "VALUES (%s, 'legacy', 'legacy@example.invalid', 'existing-hash', "
                "'Анна', 'Иванова', false, false, true, NOW(), false)",
                (legacy_id,),
            )
            self.run_command("manage.py", "migrate", "--noinput")
            self.assertEqual(
                database.execute(
                    "SELECT id, username, password, first_name, last_name, middle_name "
                    "FROM core.accounts_user WHERE id = %s",
                    (legacy_id,),
                ).fetchone(),
                (legacy_id, "legacy", "existing-hash", "Анна", "Иванова", ""),
            )
            history = database.execute(
                "SELECT app, name, applied FROM core.django_migrations ORDER BY id"
            ).fetchall()
            self.assertTrue(history)
            self.run_command("prepare_database.py")
            self.run_command("manage.py", "migrate", "--noinput")
            self.run_command("manage.py", "migrate", "--check")
            refused = self.run_command(
                "prepare_database.py", "--reset-scaffold", succeeds=False
            )
            self.assertIn("refusing to reset", refused.stderr)
            self.assertEqual(
                history,
                database.execute(
                    "SELECT app, name, applied FROM core.django_migrations ORDER BY id"
                ).fetchall(),
            )
            tables = database.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'core'"
            ).fetchall()
            self.assertIn(("accounts_user",), tables)
            self.assertNotIn(("auth_user",), tables)
            self.assertIn(("django_session",), tables)
            self.assertEqual(
                database.execute("SELECT * FROM public.auth_user").fetchall(),
                [("runtime user",)],
            )
            self.assertEqual(
                database.execute("SELECT * FROM public.django_migrations").fetchall(),
                [("runtime history",)],
            )
            self.assertEqual(
                database.execute("SELECT * FROM tenant_probe.inventory").fetchall(),
                [("tenant data",)],
            )
            self.assertEqual(
                database.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "ORDER BY tablename"
                ).fetchall(),
                [("auth_user",), ("django_migrations",)],
            )
            self.assertEqual(
                database.execute("SHOW search_path").fetchone(), original_path
            )
        with psycopg.connect(self.dsn) as fresh_connection:
            self.assertEqual(
                fresh_connection.execute("SHOW search_path").fetchone(), original_path
            )


if __name__ == "__main__":
    unittest.main()
