"""Coordinate immutable image publication followed by Helm publication."""

import json
from pathlib import Path
import tempfile

from .charts import package_chart
from .common import Error, versions
from .images import build_images, publish_images
from .observability import logger, stage
from .registry import PUBLICATION, Registry

IMAGE_PREFIX = "ghcr.io/dinikon/dnk-runtime-core"
CHART_REPOSITORY = "ghcr.io/dinikon/dnk-runtime-core/helm"


def validate_publication(record, expected):
    """Reject reuse of a chart whose immutable identity differs from this request."""
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
    """Reuse a complete chart or publish missing images before creating its chart."""
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
        logger.info("Checking chart: %s", chart_ref)
        existing = registry.manifest(chart_ref)
        if existing:
            try:
                saved = json.loads(existing["annotations"][PUBLICATION])
            except (KeyError, ValueError) as error:
                raise Error("Existing chart has no publication metadata") from error
            validate_publication(saved, record)
            logger.info("Reusing published chart: %s", chart_ref)
            return saved | {"chart_digest": registry.digest(chart_ref)}
        with stage("Publish images", app_version=app, image_tag=image_tag):
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
            with stage("Package Helm chart", chart=chart_ref):
                archive, config = package_chart(checkout.root, Path(temporary), record)
            # A second writer must never replace a version that appeared meanwhile.
            if registry.manifest(chart_ref) is not None:
                raise Error(
                    "Chart version appeared during build; retry to validate and reuse it"
                )
            with stage("Push Helm chart", chart=chart_ref):
                digest = registry.push_chart(chart_repository, archive, config, record)
        logger.info("Chart ready: %s (%s)", chart_ref, digest)
        return record | {"chart_digest": digest}
