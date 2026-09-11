"""Named local validation stages using isolated source and database helpers."""

import os
from pathlib import Path
import shutil
import sys
import tempfile

from dotenv import dotenv_values

from .check_environment import postgres, snapshot
from .common import Error, live
from .observability import stage


def check(root, full=False):
    """Run backend, Helm and frontend validation; optionally use disposable Kind."""
    for tool in ("docker", "helm", "npm") + (
        ("kind", "kubectl", "oras") if full else ()
    ):
        if shutil.which(tool) is None:
            raise Error(f"Install {tool} first; see docs/plan/ci-cd.md")
    with stage("Python formatting"):
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
            with stage("Compile backend"):
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
            with stage("Backend tests"):
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
        with stage("Package Helm chart"):
            live(
                sys.executable,
                "helm/build.py",
                "--destination",
                "dist/helm",
                cwd=copy,
                env=environment,
            )
        with stage("Helm tests"):
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
        with stage("Frontend checks", command=" ".join(args)):
            live("npm", *args, cwd=root / "frontends")
    if full:
        with stage("Kind smoke test"):
            live(sys.executable, "helm/tests/smoke.py", cwd=root)
        with stage("Migration integration"):
            live(
                sys.executable,
                "helm/tests/runtime_migrations_integration.py",
                "--runtime-image",
                "dnk-test/runtime:helm-test",
                cwd=root,
            )
        with stage("Local OCI integration"):
            live(sys.executable, "-m", "scripts.cicd.local_oci", cwd=root)
