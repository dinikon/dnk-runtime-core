"""Real PostgreSQL contention checks, called only inside a disposable test database."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import override_settings
from accounts.models import User
from accounts.services.phones import (
    add_phone,
    confirm_phone,
    set_primary_phone,
)


def race(*actions):
    """Start independent transactions together and keep connection cleanup bounded."""
    barrier = Barrier(len(actions))

    def run(action):
        """Return domain conflicts while allowing unexpected database errors to fail."""
        try:
            barrier.wait(timeout=10)
            try:
                action()
                return "ok"
            except ValidationError:
                # A conflict savepoint must leave this connection usable.
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        futures = [executor.submit(run, action) for action in actions]
        return [future.result(timeout=20) for future in futures]


def check_concurrent_phones():
    """Assert account locks, verified uniqueness and limits on actual PostgreSQL."""
    if connection.vendor != "postgresql" or not settings.DATABASES["default"][
        "NAME"
    ].startswith("dnk_core_test_"):
        raise RuntimeError(
            "Concurrency probes require a disposable CORE PostgreSQL test database."
        )
    users = []

    def create_user():
        """Create identities only in the verified disposable database."""
        user = User.objects.create_user(username="phone_probe_" + uuid4().hex)
        users.append(user)
        return user

    try:
        owner, other = create_user(), create_user()
        first = add_phone(owner, "+12025550701")
        second = add_phone(other, first.phone)
        outcomes = race(
            lambda: confirm_phone(owner, first.pk),
            lambda: confirm_phone(other, second.pk),
        )
        assert sorted(outcomes) == ["conflict", "ok"], outcomes
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.verified != second.verified
        assert first.primary == first.verified and second.primary == second.verified

        owner = create_user()
        first = add_phone(owner, "+12025550702")
        second = add_phone(owner, "+12025550703")
        assert race(
            lambda: confirm_phone(owner, first.pk),
            lambda: confirm_phone(owner, second.pk),
        ) == ["ok", "ok"]
        assert owner.phone_numbers.filter(verified=True).count() == 2
        assert owner.phone_numbers.filter(primary=True).count() == 1
        assert race(
            lambda: set_primary_phone(owner, first.pk),
            lambda: set_primary_phone(owner, second.pk),
        ) == ["ok", "ok"]
        assert owner.phone_numbers.filter(primary=True).count() == 1

        owner = create_user()
        add_phone(owner, "+12025550704")
        with override_settings(AUTH_MAX_PHONE_NUMBERS=2):
            outcomes = race(
                lambda: add_phone(owner, "+12025550705"),
                lambda: add_phone(owner, "+12025550706"),
            )
        assert sorted(outcomes) == ["conflict", "ok"], outcomes
        assert owner.phone_numbers.count() == 2
    finally:
        User.objects.filter(pk__in=[user.pk for user in users]).delete()
    print("PostgreSQL phone contention checks passed (4 scenarios).")
