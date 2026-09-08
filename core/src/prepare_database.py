"""Create Core's schema in the configured database before Django migrations."""

import argparse
import os

import django
from django.conf import settings
from django.db import connection, transaction

SCAFFOLD_TABLES = {
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "django_session",
}


def main() -> None:
    """Ensure the Core schema exists without changing other connections' settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset-scaffold",
        action="store_true",
        help="Delete only the old development Core scaffold before custom-user migrations.",
    )
    args = parser.parse_args()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnk_core.settings")
    django.setup()
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            if args.reset_scaffold:
                if not settings.DEBUG:
                    parser.error("--reset-scaffold requires CORE_DEBUG=true")
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s",
                    ["core"],
                )
                tables = {row[0] for row in cursor.fetchall()}
                if tables - SCAFFOLD_TABLES:
                    parser.error(
                        "Core contains tables beyond the temporary auth.User scaffold; "
                        "refusing to reset it."
                    )
                cursor.execute('DROP SCHEMA IF EXISTS "core" CASCADE')
            cursor.execute('CREATE SCHEMA IF NOT EXISTS "core"')
    finally:
        connection.close()


if __name__ == "__main__":
    main()
