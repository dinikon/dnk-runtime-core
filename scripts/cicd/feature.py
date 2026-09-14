"""Publish feature images and a Helm chart, then update the ArgoCD feat channel."""

from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import tempfile

from .artifacts import CHART_REPOSITORY, IMAGE_PREFIX
from .chart_registry import ChartRegistry
from .charts import package_chart
from .common import Error, run, versions
from .image_registry import DockerImageRegistry
from .images import build_images, publish_images
from .observability import log_context, logger, stage
from .registry import PUBLICATION, wait_for_manifest


def publish_feature(repo, *, registry=None, chart_registry=None, builder=None):
    """Publish a complete feature release from a pinned checkout, preserving Git refs."""
    branch_result = repo.git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch_result.returncode == 1:
        raise Error(
            "publish-feature requires a feature/* branch; detached HEAD is not supported"
        )
    if branch_result.returncode:
        raise Error("Cannot determine the current Git branch: " + branch_result.stderr)
    branch = branch_result.stdout.strip()
    if not branch.startswith("feature/") or not branch.removeprefix("feature/"):
        raise Error(
            f"publish-feature requires a feature/* branch; current branch: {branch}"
        )
    repo.clean()
    source = repo.sha()
    tag = "feat-" + source[:8]

    for tool in ("docker", "helm"):
        if shutil.which(tool) is None:
            raise Error(f"Install {tool} first; see docs/operations/ci-cd.md")
    buildx = run("docker", "buildx", "version", cwd=repo.root, check=False)
    if buildx.returncode:
        raise Error(
            "Docker Buildx is required; install/enable it before publish-feature"
        )

    registry = registry if registry is not None else DockerImageRegistry()

    def build(root, targets, environment):
        # Never inherit another branch's cache identity or a single-platform build.
        (builder or build_images)(
            root,
            targets,
            environment
            | {
                "BRANCH": branch,
                "PLATFORMS": "linux/amd64,linux/arm64",
                "SOURCE_URL": "https://github.com/dinikon/dnk-runtime-core",
            },
        )

    with log_context(branch=branch, sha=source, image_tag=tag), ExitStack() as stack:
        checkout = stack.enter_context(repo.checkout(source))
        charts = chart_registry if chart_registry is not None else stack.enter_context(ChartRegistry(CHART_REPOSITORY))
        app, chart = versions(checkout.root)
        # The g prefix keeps an all-numeric SHA with leading zeroes valid SemVer.
        chart_version = chart.split("-", 1)[0].split("+", 1)[0] + "-feat.g" + source[:8]
        with stage("Publish feature images"):
            images = publish_images(
                checkout.root, registry, IMAGE_PREFIX, app, source, tag, build
            )
        record = {
            "schema": 1, "channel": "feat", "branch": branch,
            "source_sha": source, "build_sha": source,
            "app_version": app, "chart_version": chart_version,
            "chart_repository": CHART_REPOSITORY,
            "deployment_revision": "feat-" + source, "images": images,
        }
        with stage("Publish feature Helm chart", chart_version=chart_version):
            digest = publish_feature_chart(checkout.root, charts, record)
        # A user may have switched branches or committed while the build ran.
        if repo.branch() != branch or repo.sha() != source:
            raise Error("Branch/HEAD changed during publication; feat was not updated. Retry from the intended commit")
        alias = CHART_REPOSITORY + ":feat"
        with stage("Update ArgoCD feat channel"):
            if charts.manifest(alias) is None or charts.digest(alias) != digest:
                charts.alias(CHART_REPOSITORY, digest, "feat")
            wait_for_manifest(charts, alias, digest=digest)
        for image in images.values():
            logger.info(
                "Feature image published: %s:%s (%s)",
                image["repository"],
                image["tag"],
                image["digest"],
            )
        logger.info("Feature chart published: %s:%s (%s); ArgoCD targetRevision: feat", CHART_REPOSITORY, chart_version, digest)
        return record | {"chart_digest": digest, "chart_alias": "feat"}


def publish_feature_chart(root, registry, record):
    """Reuse a verified immutable chart or package and publish it once."""
    ref = record["chart_repository"] + ":" + record["chart_version"]

    def validate(manifest):
        try:
            saved = json.loads(manifest["annotations"][PUBLICATION])
        except (KeyError, ValueError, TypeError) as error:
            raise Error(f"Chart {ref} has no valid publication metadata") from error
        # Branch is provenance: the same commit can be published from another feature branch.
        for key in ("schema", "channel", "source_sha", "build_sha", "app_version", "chart_version", "chart_repository", "deployment_revision", "images"):
            if not isinstance(saved, dict) or saved.get(key) != record[key]:
                raise Error(f"Chart {ref} differs in {key}; refusing to overwrite it")

    existing = registry.manifest(ref)
    if existing is not None:
        validate(existing)
        return registry.digest(ref)
    with tempfile.TemporaryDirectory(prefix="dnk-feature-chart-") as temporary:
        archive, config = package_chart(root, Path(temporary), record)
        if registry.manifest(ref) is not None:
            raise Error("Chart version appeared during packaging; retry to validate and reuse it")
        digest = registry.push_chart(record["chart_repository"], archive, config, record)
    validate(wait_for_manifest(registry, ref, digest=digest))
    return digest
