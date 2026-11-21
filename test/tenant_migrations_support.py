"""Изолированные графы реальных Alembic-ревизий для исторических проверок."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from alembic.script import ScriptDirectory

from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    MIGRATIONS_PATH,
    TenantMigrator,
)


@contextmanager
def tenant_migrations_through(revision: str) -> Iterator[TenantMigrator]:
    """Ограничивает реальный граф указанной ревизией без изменения production-миграций."""
    source = ScriptDirectory(str(MIGRATIONS_PATH))
    with TemporaryDirectory(prefix="dnk-tenant-history-") as directory:
        target = Path(directory)
        versions = target / "versions"
        versions.mkdir()
        for name in ("env.py", "script.py.mako"):
            copyfile(MIGRATIONS_PATH / name, target / name)
        for script in source.iterate_revisions(revision, "base"):
            copyfile(script.path, versions / Path(script.path).name)
        yield TenantMigrator(script_location=target)
