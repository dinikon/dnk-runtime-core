"""Small process and metadata helpers shared by CLI and tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[2]
STABLE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
RC = re.compile(r"^v(\d+\.\d+\.\d+)-rc\.([1-9]\d*)$")


class Error(RuntimeError):
    """An actionable failure that must not be silently retried as a new release."""


def run(*args, cwd=ROOT, env=None, check=True):
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=os.environ | (env or {}),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        # Never print argv: credentials can be passed to registry/Argo CLIs.
        raise Error(
            f"{args[0]} failed ({result.returncode}):\n{result.stderr}{result.stdout}"
        )
    return result


def live(*args, cwd=ROOT, env=None):
    result = subprocess.run(
        [str(arg) for arg in args], cwd=cwd, env=os.environ | (env or {})
    )
    if result.returncode:
        raise Error(f"{args[0]} failed ({result.returncode})")


def stable(version):
    match = STABLE.fullmatch(version)
    if not match:
        raise Error(f"Expected a stable SemVer version, got {version!r}")
    return tuple(map(int, match.groups()))


def patch(version):
    major, minor, micro = stable(version)
    return f"{major}.{minor}.{micro + 1}"


def versions(root):
    project = tomllib.loads((root / "pyproject.toml").read_text())
    chart = yaml.safe_load((root / "helm/Chart.yaml").read_text())
    app = project["project"]["version"]
    if str(chart["appVersion"]) != app:
        raise Error("project.version and helm/Chart.yaml appVersion must match")
    return app, str(chart["version"])


def set_chart_version(root, version):
    path = root / "helm/Chart.yaml"
    content, count = re.subn(
        r"(?m)^version:.*$", f"version: {version}", path.read_text()
    )
    if count != 1:
        raise Error("Expected exactly one top-level Chart.version")
    path.write_text(content)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)
