#!/usr/bin/env python3
"""Validate and package the directly installable helm/ chart without changing sources."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parent


def directory_files(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
        and path.suffix != ".pyc"
    }


def verify(root=ROOT):
    for name in ["Chart.yaml", "Chart.lock", "values.yaml", "values.schema.json"]:
        if not (root / name).is_file():
            raise ValueError(f"Chart root is missing {name}")
    if not list((root / "templates").glob("*.yaml")):
        raise ValueError("Deployment templates must be directly under helm/templates/")
    metadata = yaml.safe_load((root / "Chart.yaml").read_text())
    if metadata.get("type", "application") != "application":
        raise ValueError("The root chart must be an application")
    declared = metadata.get("dependencies", [])
    names = [dependency["name"] for dependency in declared]
    children = list((root / "charts").iterdir())
    if len(names) != len(set(names)) or set(names) != {path.name for path in children}:
        raise ValueError(
            "Dependency set mismatch: only declared infrastructure charts belong in charts/"
        )
    for dependency in declared:
        path = root / "charts" / dependency["name"] / "Chart.yaml"
        if not path.is_file():
            raise ValueError(f'Missing local dependency: {dependency["name"]}')
        child = yaml.safe_load(path.read_text())
        if child["name"] != dependency["name"] or str(child["version"]) != str(
            dependency["version"]
        ):
            raise ValueError(f'Dependency version mismatch: {dependency["name"]}')
        if dependency.get("repository"):
            raise ValueError(
                "Dependencies must be included locally; no sibling checkout or registry is required"
            )
    lock = yaml.safe_load((root / "Chart.lock").read_text())
    identity = lambda items: [
        (d["name"], str(d["version"]), d.get("repository", "")) for d in items
    ]
    if identity(declared) != identity(lock["dependencies"]):
        raise ValueError("Chart.lock differs from Chart.yaml")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, help="Write the application .tgz here"
    )
    args = parser.parse_args()
    try:
        metadata = verify()
        if args.destination is None:
            print(f'Verified directly installable {metadata["name"]} chart at helm/')
            return
        destination = args.destination.resolve()
        if destination.is_relative_to(ROOT):
            raise ValueError(
                "Package destination must be outside the source helm/ directory"
            )
        helm = os.environ.get("HELM", "helm")
        if shutil.which(helm) is None:
            raise ValueError("Helm is required; set HELM to its executable path")
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dnk-helm-package-") as temporary:
            chart = Path(temporary) / "helm"
            shutil.copytree(
                ROOT,
                chart,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
            subprocess.run(
                [helm, "package", str(chart), "--destination", str(destination)],
                check=True,
            )
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
