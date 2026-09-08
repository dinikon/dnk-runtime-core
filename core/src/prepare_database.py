"""Create Core's schema in the configured database before Django migrations."""

import os

from django.db import connection


def main() -> None:
    """Ensure the Core schema exists without changing other connections' settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnk_core.settings")
    try:
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS "core"')
    finally:
        connection.close()


if __name__ == "__main__":
    main()
