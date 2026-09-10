"""Publish immutable application images and a single-layer OCI Helm artifact."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

import yaml

from helm.build import verify
from .common import Error, run, versions, write_json

IMAGE_PREFIX = "ghcr.io/dinikon/dnk-runtime-core"
CHART_REPOSITORY = "ghcr.io/dinikon/dnk-runtime-core/helm"
HELM_CONFIG = "application/vnd.cncf.helm.config.v1+json"
HELM_LAYER = "application/vnd.cncf.helm.chart.content.v1.tar+gzip"
PUBLICATION = "io.dnk.publication"


class Registry:
    def __init__(self, plain_http=False):
        # Plain HTTP is used only by disposable local-registry integration tests.
        self.flags = ["--plain-http"] if plain_http else []

    def manifest(self, ref):
        result = run("oras", "manifest", "fetch", *self.flags, ref, check=False)
        if result.returncode:
            if any(
                text in result.stderr.lower()
                for text in ("manifest unknown", "manifest_unknown", "not found", "404")
            ):
                return None
            raise Error("Registry lookup failed: " + result.stderr)
        return json.loads(result.stdout)

    def digest(self, ref):
        return run("oras", "resolve", *self.flags, ref).stdout.strip()

    def alias(self, repository, digest, tag):
        run("oras", "tag", *self.flags, repository + "@" + digest, tag)

    def push_chart(self, repository, archive, config, publication):
        ref = repository + ":" + publication["chart_version"]
        run(
            "oras",
            "push",
            *self.flags,
            ref,
            "--config",
            f"{config.name}:{HELM_CONFIG}",
            "--annotation",
            PUBLICATION + "=" + json.dumps(publication, sort_keys=True),
            "--annotation",
            "org.opencontainers.image.source=https://github.com/dinikon/dnk-runtime-core",
            "--annotation",
            "org.opencontainers.image.revision=" + publication["source_sha"],
            "--annotation",
            "org.opencontainers.image.version=" + publication["chart_version"],
            f"{archive.name}:{HELM_LAYER}",
            cwd=archive.parent,
        )
        return self.digest(ref)


def package_chart(root, destination, publication):
    """Build a temporary chart; versioned source files and dependencies stay intact."""
    verify(root / "helm")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dnk-chart-") as temporary:
        chart = Path(temporary) / "chart"
        shutil.copytree(
            root / "helm",
            chart,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        metadata = yaml.safe_load((chart / "Chart.yaml").read_text())
        metadata.update(
            version=publication["chart_version"], appVersion=publication["app_version"]
        )
        (chart / "Chart.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False))
        values = yaml.safe_load((chart / "values.yaml").read_text())
        runtime = publication["images"]["runtime"]
        frontend = publication["images"]["frontend-runtime"]
        for component in (values["backend"], *values["workers"].values()):
            component["image"].update(
                repository=runtime["repository"], tag=runtime["tag"]
            )
        values["frontend"]["image"].update(
            repository=frontend["repository"], tag=frontend["tag"]
        )
        values["global"]["deployment"]["revision"] = publication["deployment_revision"]
        (chart / "values.yaml").write_text(yaml.safe_dump(values, sort_keys=False))
        write_json(chart / "publication.json", publication)
        run("helm", "package", chart, "--destination", destination)
        config = destination / "helm-config.json"
        write_json(config, metadata)
        return destination / f'{metadata["name"]}-{metadata["version"]}.tgz', config


def validate_publication(record, expected):
    for name in (
        "schema",
        "channel",
        "branch",
        "source_sha",
        "build_sha",
        "app_version",
        "chart_version",
        "chart_repository",
    ):
        if record.get(name) != expected.get(name):
            raise Error(
                f"Existing artifact differs in {name}; immutable versions cannot be overwritten"
            )


def publish_artifacts(
    repo,
    ref,
    branch,
    source,
    run_id,
    attempt,
    registry=None,
    image_prefix=IMAGE_PREFIX,
    chart_repository=CHART_REPOSITORY,
    builder=None,
):
    registry = registry or Registry()
    channel = "dev" if branch == "develop" else "stable" if branch == "main" else "rc"
    with repo.checkout(ref) as checkout:
        app, chart = versions(checkout.root)
        if channel == "dev":
            chart = chart.split("-", 1)[0] + f"-dev.{run_id}.{attempt}"
        build_sha = checkout.sha()
        unique_tag = f"sha-{build_sha}-{run_id}-{attempt}"
        record = {
            "schema": 1,
            "channel": channel,
            "branch": branch,
            "source_sha": source,
            "build_sha": build_sha,
            "app_version": app,
            "chart_version": chart,
            "chart_repository": chart_repository,
            "deployment_revision": f"{channel}-{build_sha}-{run_id}-{attempt}",
        }
        chart_ref = chart_repository + ":" + chart
        existing = registry.manifest(chart_ref)
        if existing:
            try:
                saved = json.loads(existing["annotations"][PUBLICATION])
            except (KeyError, ValueError) as error:
                raise Error("Existing chart has no publication metadata") from error
            validate_publication(saved, record)
            return saved | {"chart_digest": registry.digest(chart_ref)}
        images = {}
        for target in ("runtime", "frontend-runtime"):
            repository = image_prefix + "/" + target
            tag = unique_tag if channel == "dev" else app
            immutable_ref = repository + ":" + tag
            manifest = registry.manifest(immutable_ref)
            if manifest is None:
                environment = {
                    "REGISTRY_PREFIX": image_prefix,
                    "IMAGE_TAG": unique_tag,
                    "VERSION": app,
                    "SOURCE_REVISION": source,
                }
                if builder:
                    builder(checkout.root, target, environment)
                else:
                    run(
                        "docker",
                        "buildx",
                        "bake",
                        "-f",
                        "docker-bake.hcl",
                        target,
                        "--push",
                        cwd=checkout.root,
                        env=environment,
                    )
                built = repository + ":" + unique_tag
                digest = registry.digest(built)
                if tag != unique_tag:
                    # Publication concurrency serializes the only writers of this version.
                    if registry.manifest(immutable_ref) is not None:
                        raise Error(
                            "Version appeared during build; retry to validate and reuse it"
                        )
                    registry.alias(repository, digest, tag)
                manifest = registry.manifest(immutable_ref)
            annotations = (manifest or {}).get("annotations", {})
            if (
                annotations.get("org.opencontainers.image.revision") != source
                or annotations.get("org.opencontainers.image.version") != app
            ):
                raise Error(
                    f"Image {immutable_ref} belongs to a different source/version"
                )
            images[target] = {
                "repository": repository,
                "tag": tag,
                "digest": registry.digest(immutable_ref),
            }
        record["images"] = images
        with tempfile.TemporaryDirectory(prefix="dnk-oci-") as temporary:
            archive, config = package_chart(checkout.root, Path(temporary), record)
            # A second writer must never replace a version that appeared meanwhile.
            if registry.manifest(chart_ref) is not None:
                raise Error(
                    "Chart version appeared during build; retry to validate and reuse it"
                )
            digest = registry.push_chart(chart_repository, archive, config, record)
        return record | {"chart_digest": digest}


class GitHub:
    def __init__(self, repository):
        self.repository = repository

    def get_release(self, tag):
        result = run(
            "gh",
            "release",
            "view",
            tag,
            "--repo",
            self.repository,
            "--json",
            "isDraft,isPrerelease,tagName,body",
            check=False,
        )
        if result.returncode:
            if "release not found" in result.stderr.lower() or "404" in result.stderr:
                return None
            raise Error("GitHub release lookup failed: " + result.stderr)
        return json.loads(result.stdout)

    def publish(self, tag, record, changelog):
        prerelease = record["channel"] == "rc"
        body = f"{changelog.strip()}\n\n### Artifacts\n\n```json\n{json.dumps(record, indent=2)}\n```\n"
        existing = self.get_release(tag)
        if existing:
            if existing["isPrerelease"] != prerelease:
                raise Error("Existing GitHub release has a different release type")
            if not existing["isDraft"]:
                return
        with tempfile.TemporaryDirectory(prefix="dnk-release-notes-") as temporary:
            notes = Path(temporary) / "notes.md"
            notes.write_text(body)
            if existing:
                run(
                    "gh",
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    self.repository,
                    "--notes-file",
                    notes,
                )
            else:
                run(
                    "gh",
                    "release",
                    "create",
                    tag,
                    "--repo",
                    self.repository,
                    "--verify-tag",
                    "--title",
                    tag,
                    "--notes-file",
                    notes,
                    "--latest=false",
                    *(["--prerelease"] if prerelease else ["--draft"]),
                )

    def finalize(self, tag):
        run(
            "gh",
            "release",
            "edit",
            tag,
            "--repo",
            self.repository,
            "--draft=false",
            "--latest",
        )
