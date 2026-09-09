#!/usr/bin/env python3
"""Validate pinned offline dependencies and package charts using disposable copies."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

import yaml

ROOT = Path(__file__).resolve().parent


def archive_files(data):
    """Read a single-chart archive without extracting paths onto the filesystem."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        files = {}
        roots = set()
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("Unsafe chart archive path")
            roots.add(path.parts[0])
            if member.isdir():
                continue
            if not member.isfile() or len(path.parts) < 2:
                raise ValueError("Chart archives must contain regular files")
            relative = str(Path(*path.parts[1:]))
            if relative in files:
                raise ValueError("Duplicate chart archive member: " + relative)
            files[relative] = archive.extractfile(member).read()
        if len(roots) != 1 or "Chart.yaml" not in files:
            raise ValueError("Archive must contain exactly one chart")
        return files


def directory_files(chart):
    return {
        str(path.relative_to(chart)): path.read_bytes()
        for path in chart.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
        and not path.name.endswith(".pyc")
    }


def content_digest(files):
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        if name in {"Chart.yaml", "Chart.lock"}:
            content = json.dumps(yaml.safe_load(content), sort_keys=True).encode()
        digest.update(name.encode() + b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def verify_chart(files, common_digests):
    metadata = yaml.safe_load(files["Chart.yaml"])
    if metadata["name"] == "dnk-common":
        common_digests.add(content_digest(files))
    children = {}
    for path, content in files.items():
        parts = Path(path).parts
        if len(parts) < 2 or parts[0] != "charts":
            continue
        if len(parts) == 2 and parts[1].endswith(".tgz"):
            child = archive_files(content)
            child_meta = yaml.safe_load(child["Chart.yaml"])
            expected_name = f'{child_meta["name"]}-{child_meta["version"]}.tgz'
            if parts[1] != expected_name:
                raise ValueError("Archive filename does not match chart identity")
            key = child_meta["name"]
            if key in children:
                raise ValueError("Duplicate dependency: " + key)
            children[key] = child
        elif len(parts) == 3 and parts[2] == "Chart.yaml":
            prefix = "charts/" + parts[1] + "/"
            child = {
                p[len(prefix) :]: data
                for p, data in files.items()
                if p.startswith(prefix)
            }
            key = yaml.safe_load(child["Chart.yaml"])["name"]
            if key in children:
                raise ValueError("Duplicate dependency: " + key)
            children[key] = child
    declared = metadata.get("dependencies", [])
    names = [dep["name"] for dep in declared]
    if len(names) != len(set(names)) or set(names) != set(children):
        raise ValueError("Dependency set mismatch in " + metadata["name"])
    lock = yaml.safe_load(files["Chart.lock"]) if "Chart.lock" in files else None
    if lock:
        declared_lock = [
            (d["name"], str(d["version"]), d.get("repository", "")) for d in declared
        ]
        actual_lock = [
            (d["name"], str(d["version"]), d.get("repository", ""))
            for d in lock["dependencies"]
        ]
        if declared_lock != actual_lock:
            raise ValueError("Chart.lock differs from Chart.yaml")
    for dependency in declared:
        child = children[dependency["name"]]
        actual = yaml.safe_load(child["Chart.yaml"])
        if str(actual["version"]) != str(dependency["version"]):
            raise ValueError("Dependency version mismatch: " + dependency["name"])
        verify_chart(child, common_digests)


def verify(root=ROOT):
    manifest = json.loads((root / "dependencies.lock.json").read_text())
    for artifact in manifest["artifacts"]:
        relative = Path(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Artifact path must be relative to helm/")
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise ValueError("Artifact checksum mismatch: " + str(relative))
        metadata = yaml.safe_load(archive_files(data)["Chart.yaml"])
        if (
            metadata["name"] != artifact["name"]
            or str(metadata["version"]) != artifact["version"]
        ):
            raise ValueError("Artifact identity mismatch: " + str(relative))
    charts = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "Chart.yaml").is_file()
    ]
    common_digests = set()
    for chart in charts:
        verify_chart(directory_files(chart), common_digests)
    if common_digests != {manifest["common_content_sha256"]}:
        raise ValueError(
            "All dnk-common copies must have the pinned, identical content"
        )
    return charts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        help="Write release .tgz artifacts here; never modifies chart sources",
    )
    args = parser.parse_args()
    try:
        charts = verify()
        if not args.destination:
            print("Verified pinned dependencies and common-library compatibility")
            return
        destination = args.destination.resolve()
        if destination.is_relative_to(ROOT):
            parser.error(
                "Package destination must be outside the source helm directory"
            )
        helm = os.environ.get("HELM", "helm")
        if not shutil.which(helm):
            parser.error("Helm is required; set HELM to its executable path")
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dnk-helm-build-") as directory:
            staged = Path(directory) / "helm"
            shutil.copytree(
                ROOT,
                staged,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
            for source in charts:
                chart = staged / source.name
                if chart.name == "dnk-platform":
                    for name in ["dnk-common", "dnk-control-plane"]:
                        subprocess.run(
                            [
                                helm,
                                "package",
                                str(chart / "charts" / name),
                                "--destination",
                                str(destination),
                            ],
                            check=True,
                        )
                subprocess.run(
                    [helm, "package", str(chart), "--destination", str(destination)],
                    check=True,
                )
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
