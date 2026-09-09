"""Serialize schema preparation and migrations on one PostgreSQL session."""

import math
import time
from contextlib import contextmanager

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, OperationalError, connections

# Database-local and stable across releases, replicas and Helm release names.
MIGRATION_LOCK_ID = int.from_bytes(b"dnk:core", "big")
CONNECT_TIMEOUT_SECONDS = 5
POLL_INTERVAL_SECONDS = 1


@contextmanager
def pinned_session(connection):
    """Prevent Django from reopening a connection that no longer owns the lock."""
    missing = object()
    original = connection.__dict__.get("connect", missing)

    def refuse_reconnection():
        raise CommandError(
            "Core migration database session was lost; restart preparation."
        )

    connection.connect = refuse_reconnection
    try:
        yield
    finally:
        if original is missing:
            del connection.connect
        else:
            connection.connect = original


class Command(BaseCommand):
    help = "Wait for PostgreSQL, lock Core migrations, create its schema and migrate."
    # Database access must begin only inside our bounded connection wait.
    requires_system_checks = []
    requires_migrations_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait-timeout",
            type=int,
            default=300,
            help="Seconds to wait for PostgreSQL and the migration lock (minimum 2).",
        )

    def handle(self, *args, **options):
        wait_timeout = options["wait_timeout"]
        if wait_timeout < 2:
            raise CommandError("--wait-timeout must be at least 2 seconds.")
        connection = connections[DEFAULT_DB_ALIAS]
        if connection.vendor != "postgresql":
            raise CommandError("prepare_deployment requires PostgreSQL.")
        if connection.in_atomic_block or not connection.settings_dict["AUTOCOMMIT"]:
            raise CommandError("prepare_deployment requires an autocommit connection.")
        if connection.settings_dict["OPTIONS"].get("pool"):
            raise CommandError(
                "prepare_deployment requires a direct, unpooled connection."
            )

        deadline = time.monotonic() + wait_timeout
        original_options = connection.settings_dict["OPTIONS"]
        try:
            connection.close()
            self.wait_for_database(connection, deadline, original_options)
            with pinned_session(connection):
                self.prepare(connection, deadline, options["verbosity"])
        except CommandError:
            raise
        except Exception as error:
            # Drivers and migrations can include credentials or row data in errors.
            raise CommandError(
                f"Core database preparation failed ({type(error).__name__}); "
                "inspect PostgreSQL and migration diagnostics before retrying."
            ) from None
        finally:
            try:
                connection.close()
            finally:
                connection.settings_dict["OPTIONS"] = original_options
        self.stdout.write(self.style.SUCCESS("Core database preparation complete."))

    def wait_for_database(self, connection, deadline, original_options):
        """Retry connection failures only, with a bounded libpq connect timeout."""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CommandError(
                    "Timed out waiting for the Core PostgreSQL database."
                )
            # libpq rounds timeouts below two seconds up to two seconds. A final
            # connection attempt can therefore overrun the deadline by <2 seconds.
            connection.settings_dict["OPTIONS"] = {
                **original_options,
                "connect_timeout": max(
                    2, min(CONNECT_TIMEOUT_SECONDS, math.ceil(remaining))
                ),
            }
            try:
                connection.ensure_connection()
                return
            except (OperationalError, connection.Database.OperationalError):
                connection.close()
                self.pause(deadline)

    def prepare(self, connection, deadline, verbosity):
        """Hold a session lock across Django's own per-migration transactions."""
        session = connection.connection
        locked = False
        try:
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_try_advisory_lock(%s)", [MIGRATION_LOCK_ID]
                    )
                    locked = cursor.fetchone()[0]
                if locked:
                    break
                self.pause(deadline)
            if not locked:
                raise CommandError("Timed out waiting for the Core migration lock.")

            with connection.cursor() as cursor:
                cursor.execute('CREATE SCHEMA IF NOT EXISTS "core"')
            call_command(
                "migrate",
                database=DEFAULT_DB_ALIAS,
                interactive=False,
                verbosity=verbosity,
                stdout=self.stdout,
                stderr=self.stderr,
            )
            if connection.connection is not session or session.closed:
                raise CommandError(
                    "Core migration database session was lost; restart preparation."
                )
        finally:
            if locked and not session.closed:
                # Use the original driver's session directly: cleanup must never
                # open a new Django connection, including after migration failure.
                try:
                    with session.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID]
                        )
                except (DatabaseError, connection.Database.Error):
                    self.stderr.write(
                        "Closing database session to release the Core migration lock."
                    )

    @staticmethod
    def pause(deadline):
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(POLL_INTERVAL_SECONDS, remaining))
