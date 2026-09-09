"""Run runtime migration checks against an isolated PostgreSQL and published image.

Usage: python helm/tests/runtime_migrations_integration.py
Docker must be available. The script never accepts an existing database address;
its network, database and runtime test containers are created and removed here.
"""

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_RELATIVE = Path("helm/dnk-runtime-core/files")


def docker(*args, check=True):
    result = subprocess.run(["docker", *args], text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "Docker command failed"
        )
    return result


def run_in_docker(image):
    suffix = uuid.uuid4().hex[:12]
    network = "dnk-migration-tests-" + suffix
    postgres = network + "-postgres"
    runtime = network + "-runtime"
    password = secrets.token_urlsafe(30)
    with tempfile.TemporaryDirectory(prefix="dnk-migration-tests-") as directory:
        env_file = Path(directory) / "database.env"
        env_file.write_text(
            "\n".join(
                [
                    "POSTGRES_USER=dnk_tests",
                    "POSTGRES_DB=dnk_helm_migration_tests",
                    "POSTGRES_PASSWORD=" + password,
                    "DB_HOST=postgres",
                    "DB_PORT=5432",
                    "DB_USERNAME=dnk_tests",
                    "DB_DATABASE=dnk_helm_migration_tests",
                    "DB_PASSWORD=" + password,
                    "SCHEMA_PREFIX=dnk_",
                    "PYTHONPATH=/app",
                    "DNK_MIGRATIONS_DISPOSABLE=1",
                    "SQLALCHEMY_ECHO=false",
                    "",
                ]
            )
        )
        env_file.chmod(0o600)
        try:
            docker("network", "create", network)
            docker(
                "run",
                "-d",
                "--name",
                postgres,
                "--network",
                network,
                "--network-alias",
                "postgres",
                "--env-file",
                str(env_file),
                "postgres:16-alpine",
            )
            deadline = time.monotonic() + 60
            while docker(
                "exec",
                postgres,
                "pg_isready",
                "-U",
                "dnk_tests",
                "-d",
                "dnk_helm_migration_tests",
                check=False,
            ).returncode:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "Disposable PostgreSQL did not become ready within 60 seconds"
                    )
                time.sleep(0.5)
            process = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    runtime,
                    "--network",
                    network,
                    "--env-file",
                    str(env_file),
                    "--mount",
                    "type=bind,source={},target=/dnk-source,readonly".format(ROOT),
                    "--entrypoint",
                    "python",
                    image,
                    "/dnk-source/helm/tests/runtime_migrations_integration.py",
                    "--inside",
                ]
            )
            if process.returncode:
                raise RuntimeError("Runtime migration integration checks failed")
        finally:
            docker("rm", "-f", "-v", runtime, check=False)
            docker("rm", "-f", "-v", postgres, check=False)
            docker("network", "rm", network, check=False)


def inside_tests():
    if (
        os.environ.get("DNK_MIGRATIONS_DISPOSABLE") != "1"
        or os.environ.get("DB_DATABASE") != "dnk_helm_migration_tests"
    ):
        raise RuntimeError(
            "Integration tests require the disposable database created by this script"
        )
    # Import dependencies from the published image, not the checkout mounted below.
    import asyncio
    import importlib.util
    import unittest

    from sqlalchemy import event, text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    runner_path = ROOT / RUNTIME_RELATIVE / "migrate.py"
    spec = importlib.util.spec_from_file_location("helm_runtime_migrate", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    database_url = URL.create(
        "postgresql+asyncpg",
        username=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_DATABASE"],
    )

    class RuntimeMigrationPostgresTests(unittest.IsolatedAsyncioTestCase):
        async def asyncSetUp(self):
            self.engine = create_async_engine(database_url, poolclass=NullPool)
            self.admin = create_async_engine(database_url, poolclass=NullPool)
            async with self.admin.begin() as connection:
                schemas = await connection.scalars(
                    text(
                        "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
                        "AND nspname != 'information_schema'"
                    )
                )
                for schema in schemas:
                    quoted = connection.dialect.identifier_preparer.quote(schema)
                    await connection.execute(text("DROP SCHEMA " + quoted + " CASCADE"))
                await connection.execute(text("CREATE SCHEMA public"))
                await connection.execute(
                    text("CREATE TABLE public.protected (value text)")
                )
                await connection.execute(
                    text("INSERT INTO public.protected VALUES ('preserved')")
                )
                await connection.execute(text("CREATE SCHEMA tenant_unmanaged"))
                await connection.execute(
                    text("CREATE TABLE tenant_unmanaged.protected (value text)")
                )
                await connection.execute(
                    text(
                        "INSERT INTO tenant_unmanaged.protected VALUES ('tenant-preserved')"
                    )
                )

        async def asyncTearDown(self):
            await self.engine.dispose()
            await self.admin.dispose()

        async def scalar(self, statement, values=None):
            async with self.admin.connect() as connection:
                return await connection.scalar(text(statement), values or {})

        async def no_tenants(self, connection):
            return []

        async def noop(self, *args):
            return None

        async def cli(self, *, success=True):
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(runner_path),
                "--wait-timeout",
                "10",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), 45)
            output = stdout.decode() + stderr.decode()
            self.assertNotIn(os.environ["DB_PASSWORD"], output)
            if success:
                self.assertEqual(process.returncode, 0, output)
            else:
                self.assertNotEqual(process.returncode, 0, output)
            return output

        async def seed_tenants(self, *, count=2, missing_last=False):
            # Use actual public tables bootstrapped by the published image's models.
            await self.cli()
            ids = [uuid.UUID(int=index + 1) for index in range(count)]
            async with self.admin.begin() as connection:
                for index, tenant_id in enumerate(ids):
                    await connection.execute(
                        text(
                            "INSERT INTO public.tenants (id, name, external_id) "
                            "VALUES (:id, :name, :external)"
                        ),
                        {
                            "id": tenant_id,
                            "name": "integration tenant",
                            "external": "test-" + str(index),
                        },
                    )
                    if not (missing_last and index == count - 1):
                        await connection.execute(
                            text('CREATE SCHEMA "dnk_{}"'.format(tenant_id.hex))
                        )
            return ids

        async def test_published_image_bootstrap_migrations_repeat_preserve_existing_data(
            self,
        ):
            ids = await self.seed_tenants()
            await self.cli()
            await self.cli()
            for tenant_id in ids:
                revision = await self.scalar(
                    'SELECT version_num FROM "dnk_{}".alembic_version'.format(
                        tenant_id.hex
                    )
                )
                self.assertTrue(revision)
                self.assertIsNotNone(
                    await self.scalar(
                        "SELECT to_regclass(:name)",
                        {"name": "dnk_{}.warehouses".format(tenant_id.hex)},
                    )
                )
            self.assertEqual(
                await self.scalar("SELECT value FROM public.protected"), "preserved"
            )
            self.assertEqual(
                await self.scalar("SELECT value FROM tenant_unmanaged.protected"),
                "tenant-preserved",
            )

        async def test_published_image_missing_second_tenant_rolls_back_first(self):
            ids = await self.seed_tenants(missing_last=True)
            output = await self.cli(success=False)
            self.assertIn("batch rolled back", output)
            self.assertIsNone(
                await self.scalar(
                    "SELECT to_regclass(:name)",
                    {"name": "dnk_{}.alembic_version".format(ids[0].hex)},
                )
            )
            self.assertIsNone(
                await self.scalar(
                    "SELECT to_regclass(:name)",
                    {"name": "dnk_{}.warehouses".format(ids[0].hex)},
                )
            )
            self.assertEqual(
                await self.scalar("SELECT value FROM public.protected"), "preserved"
            )

        async def test_callbacks_share_physical_connection_transaction_and_lock(self):
            pids, transactions = [], []

            async def observe(connection):
                pids.append(await connection.scalar(text("SELECT pg_backend_pid()")))
                transactions.append(
                    await connection.scalar(text("SELECT txid_current()"))
                )
                self.assertTrue(connection.in_transaction())
                self.assertTrue(
                    await connection.scalar(
                        text(
                            "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() "
                            "AND locktype='advisory' AND granted)"
                        )
                    )
                )

            async def bootstrap(connection):
                await observe(connection)
                await connection.execute(
                    text("CREATE TABLE public.batch_created (value integer)")
                )

            async def tenants(connection):
                await observe(connection)
                return [1, 2]

            async def upgrade(connection, tenant_id):
                await observe(connection)
                await connection.execute(
                    text("INSERT INTO public.batch_created VALUES (:value)"),
                    {"value": tenant_id},
                )

            await runner.prepare(self.engine, bootstrap, tenants, upgrade, 5)
            self.assertEqual(len(pids), 4)
            self.assertEqual(len(set(pids)), 1)
            self.assertEqual(len(set(transactions)), 1)
            self.assertEqual(
                await self.scalar("SELECT count(*) FROM public.batch_created"), 2
            )

        async def test_second_tenant_failure_rolls_back_bootstrap_and_entire_batch(
            self,
        ):
            async def bootstrap(connection):
                await connection.execute(
                    text("CREATE TABLE public.batch_created (value integer)")
                )

            async def tenants(connection):
                return [1, 2]

            async def upgrade(connection, tenant_id):
                await connection.execute(
                    text("INSERT INTO public.batch_created VALUES (:value)"),
                    {"value": tenant_id},
                )
                if tenant_id == 2:
                    raise RuntimeError("injected second tenant failure")

            with self.assertRaisesRegex(RuntimeError, "second tenant failure"):
                await runner.prepare(self.engine, bootstrap, tenants, upgrade, 5)
            self.assertIsNone(
                await self.scalar("SELECT to_regclass('public.batch_created')")
            )
            self.assertEqual(
                await self.scalar("SELECT value FROM public.protected"), "preserved"
            )

        async def test_concurrent_batches_serialize_before_any_bootstrap(self):
            active, peak, pids = 0, 0, set()

            async def bootstrap(connection):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                pids.add(await connection.scalar(text("SELECT pg_backend_pid()")))
                await asyncio.sleep(0.2)
                await connection.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS public.batch_created (value integer)"
                    )
                )
                await connection.execute(
                    text("INSERT INTO public.batch_created VALUES (1)")
                )
                active -= 1

            await asyncio.wait_for(
                asyncio.gather(
                    *[
                        runner.prepare(
                            self.engine, bootstrap, self.no_tenants, self.noop, 5
                        )
                        for _ in range(3)
                    ]
                ),
                10,
            )
            self.assertEqual(peak, 1)
            self.assertEqual(len(pids), 3)
            self.assertEqual(
                await self.scalar("SELECT count(*) FROM public.batch_created"), 3
            )

        async def test_global_lock_timeout_does_not_start_bootstrap(self):
            called = False

            async def unexpected(connection):
                nonlocal called
                called = True

            async with self.admin.begin() as blocker:
                await blocker.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": runner.LOCK_KEY}
                )
                started = time.monotonic()
                with self.assertRaisesRegex(TimeoutError, "lock timeout"):
                    await runner.prepare(
                        self.engine, unexpected, self.no_tenants, self.noop, 0.3
                    )
                self.assertLess(time.monotonic() - started, 2)
            self.assertFalse(called)
            await runner.prepare(self.engine, self.noop, self.no_tenants, self.noop, 2)

        async def test_tenant_lock_timeout_rolls_back_bootstrap(self):
            async def bootstrap(connection):
                await connection.execute(
                    text("CREATE TABLE public.batch_created (value integer)")
                )

            async def tenants(connection):
                return [42]

            async def upgrade(connection, tenant_id):
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": tenant_id}
                )

            async with self.admin.begin() as blocker:
                await blocker.execute(text("SELECT pg_advisory_xact_lock(42)"))
                started = time.monotonic()
                with self.assertRaises(Exception):
                    await runner.prepare(self.engine, bootstrap, tenants, upgrade, 0.3)
                self.assertLess(time.monotonic() - started, 2)
            self.assertIsNone(
                await self.scalar("SELECT to_regclass('public.batch_created')")
            )

        async def test_lost_connection_rolls_back_without_reconnecting(self):
            connections, upgrades = [], []
            event.listen(
                self.engine.sync_engine,
                "connect",
                lambda dbapi, record: connections.append(record),
            )

            async def bootstrap(connection):
                await connection.execute(
                    text("CREATE TABLE public.batch_created (value integer)")
                )

            async def tenants(connection):
                return [1, 2]

            async def upgrade(connection, tenant_id):
                upgrades.append(tenant_id)
                pid = await connection.scalar(text("SELECT pg_backend_pid()"))
                self.assertTrue(
                    await self.scalar("SELECT pg_terminate_backend(:pid)", {"pid": pid})
                )
                await connection.execute(
                    text("INSERT INTO public.batch_created VALUES (1)")
                )

            with self.assertRaises(Exception):
                await runner.prepare(self.engine, bootstrap, tenants, upgrade, 5)
            self.assertEqual(
                len(connections),
                1,
                "No retry or reconnect is allowed after obtaining the transaction",
            )
            self.assertEqual(upgrades, [1])
            self.assertIsNone(
                await self.scalar("SELECT to_regclass('public.batch_created')")
            )

        async def test_concurrent_cli_processes_on_published_image(self):
            ids = await self.seed_tenants()
            await asyncio.wait_for(asyncio.gather(self.cli(), self.cli()), 60)
            for tenant_id in ids:
                self.assertTrue(
                    await self.scalar(
                        'SELECT version_num FROM "dnk_{}".alembic_version'.format(
                            tenant_id.hex
                        )
                    )
                )

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeMigrationPostgresTests)
    )
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-image", default="ghcr.io/dinikon/runtime/runtime:latest"
    )
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inside:
        inside_tests()
    else:
        run_in_docker(args.runtime_image)
