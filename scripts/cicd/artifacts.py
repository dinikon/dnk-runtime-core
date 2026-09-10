"""Publish immutable application images and a single-layer OCI Helm artifact."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import quote

import httpx
import yaml

from helm.build import verify
from .common import Error, live, run, versions, write_json

IMAGE_PREFIX = "ghcr.io/dinikon/dnk-runtime-core"
CHART_REPOSITORY = "ghcr.io/dinikon/dnk-runtime-core/helm"
HELM_CONFIG = "application/vnd.cncf.helm.config.v1+json"
HELM_LAYER = "application/vnd.cncf.helm.chart.content.v1.tar+gzip"
PUBLICATION = "io.dnk.publication"
REGISTRY_RETRY_DELAYS = (1, 2, 4, 8, 15, 30)


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
            raise Error(f"Registry lookup failed for {ref}: " + result.stderr)
        return json.loads(result.stdout)

    def digest(self, ref):
        return run("oras", "resolve", *self.flags, ref).stdout.strip()

    def alias(self, repository, digest, tag):
        run("oras", "tag", *self.flags, repository + "@" + digest, tag)

    def push_chart(self, repository, archive, config, publication):
        ref = repository + ":" + publication["chart_version"]
        live(
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
        wait_for_manifest(self, ref)
        return self.digest(ref)


def wait_for_manifest(registry, ref, *, digest=None):
    """A successful push may become readable later; retry only missing manifests."""
    for number, delay in enumerate((0, *REGISTRY_RETRY_DELAYS), 1):
        if delay:
            print(
                f"Waiting for registry manifest {ref}; retry {number} in {delay}s",
                flush=True,
            )
            time.sleep(delay)
        manifest = registry.manifest(ref)
        if manifest is not None and (digest is None or registry.digest(ref) == digest):
            return manifest
    raise Error(
        f"Registry still does not expose {ref}"
        + (f" at {digest}" if digest else "")
        + f" after {number} checks; "
        "the push may have succeeded. Retry publication without deleting artifacts"
    )


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


def build_images(root, targets, environment):
    """One Bake invocation lets BuildKit schedule independent images in parallel."""
    print("Building and publishing images: " + ", ".join(targets), flush=True)
    live(
        "docker",
        "buildx",
        "bake",
        "-f",
        "docker-bake.hcl",
        *targets,
        "--push",
        "--progress=plain",
        cwd=root,
        env=environment,
    )


def published_image(registry, repository, tag, source, app, *, wait=False):
    """Reuse a published tag only when its full source SHA and version match."""
    ref = repository + ":" + tag
    manifest = wait_for_manifest(registry, ref) if wait else registry.manifest(ref)
    if manifest is None:
        return None
    annotations = manifest.get("annotations", {})
    if (
        annotations.get("org.opencontainers.image.revision") != source
        or annotations.get("org.opencontainers.image.version") != app
    ):
        raise Error(
            f"Image {ref} belongs to a different source/version; refusing to overwrite it"
        )
    digest = registry.digest(ref)
    print(f"Image ready: {ref} ({digest})", flush=True)
    return {"repository": repository, "tag": tag, "digest": digest}


def publish_images(root, registry, image_prefix, app, source, tag, builder):
    images, missing = {}, []

    def collect(target, *, wait=False):
        return published_image(
            registry,
            image_prefix + "/" + target,
            tag,
            source,
            app,
            wait=wait,
        )

    for target in ("runtime", "frontend-runtime"):
        print(f"Checking image: {image_prefix}/{target}:{tag}", flush=True)
        image = collect(target)
        if image is None:
            missing.append(target)
        else:
            images[target] = image
    if missing:
        environment = {
            "REGISTRY_PREFIX": image_prefix,
            "IMAGE_TAG": tag,
            "VERSION": app,
            "SOURCE_REVISION": source,
        }
        try:
            builder(root, missing, environment)
        except Error:
            # Each image is already pushed under its final tag. A later attempt
            # reuses either completed image, including one that becomes visible late.
            for target in missing:
                try:
                    collect(target, wait=True)
                except Error as error:
                    print(
                        f"Could not recover image {target}: {error}",
                        flush=True,
                    )
            raise
        for target in missing:
            image = collect(target, wait=True)
            if image is None:
                raise Error(f"Build completed without publishing image {target}")
            images[target] = image
    return images


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
        image_tag = f"dev-{source[:8]}" if channel == "dev" else app
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
        print(f"Checking chart: {chart_ref}", flush=True)
        existing = registry.manifest(chart_ref)
        if existing:
            try:
                saved = json.loads(existing["annotations"][PUBLICATION])
            except (KeyError, ValueError) as error:
                raise Error("Existing chart has no publication metadata") from error
            validate_publication(saved, record)
            print(f"Reusing published chart: {chart_ref}", flush=True)
            return saved | {"chart_digest": registry.digest(chart_ref)}
        record["images"] = publish_images(
            checkout.root,
            registry,
            image_prefix,
            app,
            source,
            image_tag,
            builder or build_images,
        )
        with tempfile.TemporaryDirectory(prefix="dnk-oci-") as temporary:
            print(f"Packaging chart: {chart_ref}", flush=True)
            archive, config = package_chart(checkout.root, Path(temporary), record)
            # A second writer must never replace a version that appeared meanwhile.
            if registry.manifest(chart_ref) is not None:
                raise Error(
                    "Chart version appeared during build; retry to validate and reuse it"
                )
            print(f"Publishing chart: {chart_ref}", flush=True)
            digest = registry.push_chart(chart_repository, archive, config, record)
        print(f"Chart ready: {chart_ref} ({digest})", flush=True)
        return record | {"chart_digest": digest}


def current_publication(repo, record):
    repo.fetch()
    return repo.sha("origin/" + record["branch"]) == record["build_sha"]


def publish_channel_aliases(repo, record, registry=None):
    """Publish registry pointers for pull-based consumers, without cluster access."""
    channel = record["channel"]
    if channel == "rc":
        return False
    if record["branch"] != {"dev": "develop", "stable": "main"}.get(channel):
        raise Error("Invalid publication channel/branch")
    registry = registry or Registry()
    aliases = (
        [(record["chart_repository"], record["chart_digest"], "dev")]
        if channel == "dev"
        else [
            (
                record["images"][target]["repository"],
                record["images"][target]["digest"],
                "latest",
            )
            for target in ("runtime", "frontend-runtime")
        ]
    )
    for repository, digest, tag in aliases:
        if not current_publication(repo, record):
            print(
                "A newer branch HEAD exists; leaving floating tags unchanged",
                flush=True,
            )
            return False
        ref = repository + ":" + tag
        if registry.manifest(ref) is None or registry.digest(ref) != digest:
            registry.alias(repository, digest, tag)
        wait_for_manifest(registry, ref, digest=digest)
        print(f"Published alias: {ref} ({digest})", flush=True)
    return True


class GitHub:
    def __init__(self, repository):
        self.repository = repository

    def get_release(self, tag):
        """Read release readiness without requiring GitHub CLI locally."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        url = "https://api.github.com/repos/" + self.repository
        try:
            with httpx.Client(
                headers=headers, timeout=30, follow_redirects=True
            ) as client:
                result = client.get(url + "/releases/tags/" + quote(tag, safe=""))
                if result.status_code == 404:
                    # The tag endpoint only promises published releases. Listing
                    # also finds drafts and distinguishes missing releases from
                    # inaccessible repositories, which GitHub also hides as 404.
                    page = 1
                    while True:
                        result = client.get(
                            url + "/releases", params={"per_page": 100, "page": page}
                        )
                        result.raise_for_status()
                        release = next(
                            (item for item in result.json() if item["tag_name"] == tag),
                            None,
                        )
                        if release is not None:
                            break
                        if "next" not in result.links:
                            return None
                        page += 1
                else:
                    result.raise_for_status()
                    release = result.json()
        except httpx.HTTPStatusError as error:
            raise Error(
                f"GitHub release lookup failed (HTTP {error.response.status_code}); "
                "check GITHUB_REPOSITORY, GH_TOKEN or GITHUB_TOKEN with Contents: read "
                "access, and GitHub API rate limits"
            ) from error
        except httpx.RequestError as error:
            raise Error(
                "GitHub release lookup failed; check the network connection and retry"
            ) from error
        return {
            "isDraft": release["draft"],
            "isPrerelease": release["prerelease"],
            "tagName": release["tag_name"],
            "body": release.get("body") or "",
        }

    def publish(self, tag, record, changelog, *, latest=False):
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
                    "--draft=false",
                    "--latest" if latest and not prerelease else "--latest=false",
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
                    "--latest" if latest and not prerelease else "--latest=false",
                    "--draft=false",
                    *(["--prerelease"] if prerelease else []),
                )
