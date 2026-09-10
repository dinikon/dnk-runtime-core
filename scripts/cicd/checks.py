"""Local checks, with isolated source/configuration and a disposable PostgreSQL."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid

from dotenv import dotenv_values

from .common import Error, live, run


@contextmanager
def postgres():
    name = "dnk-check-" + uuid.uuid4().hex[:12]
    password = uuid.uuid4().hex
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
        run("docker", "rm", "-f", name, check=False)


def snapshot(root, destination):
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


def check(root, full=False):
    for tool in ("docker", "helm", "npm") + (
        ("kind", "kubectl", "oras") if full else ()
    ):
        if shutil.which(tool) is None:
            raise Error(f"Install {tool} first; see docs/plan/ci-cd.md")
    live(
        sys.executable,
        "-m",
        "black",
        "--check",
        "src",
        "test",
        "migrations",
        "scripts",
        cwd=root,
    )
    with tempfile.TemporaryDirectory(prefix="dnk-check-source-") as directory:
        copy = Path(directory)
        snapshot(root, copy)
        environment = {
            key: value
            for key, value in dotenv_values(copy / ".env").items()
            if value is not None
        }
        environment.update(PYTHONPATH=str(copy) + os.pathsep + str(copy / "src"))
        with postgres() as database:
            environment.update(database)
            live(
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "src",
                "migrations",
                cwd=copy,
                env=environment,
            )
            live(
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "test",
                "-p",
                "test_*.py",
                "-v",
                cwd=copy,
                env=environment,
            )
        live(
            sys.executable,
            "helm/build.py",
            "--destination",
            "dist/helm",
            cwd=copy,
            env=environment,
        )
        live(
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "helm/tests",
            "-p",
            "test_*.py",
            "-v",
            cwd=copy,
            env=environment,
        )
    for args in (
        ("ci",),
        ("run", "lint:console"),
        ("run", "typecheck:console"),
        ("run", "build:console"),
    ):
        live("npm", *args, cwd=root / "frontends")
    if full:
        live(sys.executable, "helm/tests/smoke.py", cwd=root)
        live(
            sys.executable,
            "helm/tests/runtime_migrations_integration.py",
            "--runtime-image",
            "dnk-test/runtime:helm-test",
            cwd=root,
        )
        live(sys.executable, "-m", "scripts.cicd.local_oci", cwd=root)
