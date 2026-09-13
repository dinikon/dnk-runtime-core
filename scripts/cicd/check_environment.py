"""Isolated source snapshots and disposable integration services for checks."""

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
        for database in ("control_plane_test", "global_test"):
            run("docker", "exec", name, "createdb", "-U", "postgres", database)
        yield {
            "TEST_POSTGRES_URL": f"postgresql+asyncpg://postgres:{password}@127.0.0.1:{port}/inventory_test",
            "TEST_CP_POSTGRES_URL": f"postgresql+asyncpg://postgres:{password}@127.0.0.1:{port}/control_plane_test",
            "DNK_TEST_DATABASE_URL": f"postgresql+asyncpg://postgres:{password}@127.0.0.1:{port}/global_test",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": port,
            "DB_USERNAME": "postgres",
            "DB_PASSWORD": password,
            "DB_DATABASE": "inventory_test",
        }
    finally:
        logger.info("Removing disposable PostgreSQL: %s", name)
        run("docker", "rm", "-f", "--volumes", name, check=False)


@contextmanager
def integration_stores():
    """Exercise Redis atomic consumption and real RabbitMQ delivery in CI."""
    tag = uuid.uuid4().hex[:12]
    redis_name, rabbit_name = f"dnk-check-redis-{tag}", f"dnk-check-rabbit-{tag}"
    password = uuid.uuid4().hex
    names = []
    try:
        for name, port, image, extra in (
            (redis_name, 6379, "redis:7-alpine", ()),
            (
                rabbit_name,
                5672,
                "rabbitmq:3.13-management-alpine",
                (
                    "-e",
                    "RABBITMQ_DEFAULT_USER=runtime_test",
                    "-e",
                    "RABBITMQ_DEFAULT_PASS=" + password,
                    "-e",
                    "RABBITMQ_DEFAULT_VHOST=runtime-control-plane-test",
                ),
            ),
        ):
            names.append(name)
            run(
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--publish",
                f"127.0.0.1::{port}",
                *extra,
                image,
            )
        deadline = time.monotonic() + 90
        for name, exec_options, command in (
            (redis_name, (), ("redis-cli", "ping")),
            (
                rabbit_name,
                ("--user", "rabbitmq"),
                ("rabbitmq-diagnostics", "-q", "check_port_connectivity"),
            ),
        ):
            while (
                probe := run(
                    "docker", "exec", *exec_options, name, *command, check=False
                )
            ).returncode:
                if time.monotonic() > deadline:
                    raise Error(
                        f"Disposable integration store {name} did not become ready: "
                        + (probe.stderr + probe.stdout)[-2000:]
                    )
                time.sleep(1)
        redis_port = (
            run("docker", "port", redis_name, "6379/tcp")
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        rabbit_port = (
            run("docker", "port", rabbit_name, "5672/tcp")
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        yield {
            "TEST_REDIS_URL": f"redis://127.0.0.1:{redis_port}/0",
            "TEST_CP_RABBITMQ_URL": f"amqp://runtime_test:{password}@127.0.0.1:{rabbit_port}/runtime-control-plane-test",
        }
    finally:
        for name in reversed(names):
            logger.info("Removing disposable integration store: %s", name)
            run("docker", "rm", "-f", "--volumes", name, check=False)


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
