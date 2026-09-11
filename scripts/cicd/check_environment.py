"""Isolated source snapshots and disposable PostgreSQL for local checks."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import time
import uuid

from .common import Error, run
from .observability import logger


@contextmanager
def postgres():
    """Yield credentials for a disposable local database, then remove its container."""
    name = "dnk-check-" + uuid.uuid4().hex[:12]
    password = uuid.uuid4().hex
    logger.info("Starting disposable PostgreSQL: %s", name)
    try:
        run(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--publish",
            "127.0.0.1::5432",
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            "POSTGRES_DB=inventory_test",
            "-e",
            "POSTGRES_PASSWORD=" + password,
            "postgres:16-alpine",
        )
        port = run("docker", "port", name, "5432/tcp").stdout.strip().rsplit(":", 1)[1]
        deadline = time.monotonic() + 60
        while run(
            "docker",
            "exec",
            name,
            "pg_isready",
            "-U",
            "postgres",
            "-d",
            "inventory_test",
            check=False,
        ).returncode:
            if time.monotonic() > deadline:
                raise Error("Disposable PostgreSQL did not become ready")
            time.sleep(1)
        yield {
            "TEST_POSTGRES_URL": f"postgresql+asyncpg://postgres:{password}@127.0.0.1:{port}/inventory_test",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": port,
            "DB_USERNAME": "postgres",
            "DB_PASSWORD": password,
            "DB_DATABASE": "inventory_test",
        }
    finally:
        logger.info("Removing disposable PostgreSQL: %s", name)
        run("docker", "rm", "-f", name, check=False)


def snapshot(root, destination):
    """Copy tracked and unignored files and use the test configuration in isolation."""
    files = run(
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", cwd=root
    ).stdout.split("\0")
    for name in set(files):
        if not name or Path(name).name == ".DS_Store":
            continue
        source = root / name
        if source.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    # A settings module searches upwards from __file__; run it from this copy.
    shutil.copy2(root / "temaplate.dev.env", destination / ".env")
