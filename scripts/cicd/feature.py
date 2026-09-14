"""Publish only container images from a clean, local feature branch."""

import shutil

from .artifacts import IMAGE_PREFIX
from .common import Error, run, versions
from .image_registry import DockerImageRegistry
from .images import build_images, publish_images
from .observability import log_context, logger, stage


def publish_feature(repo, *, registry=None, builder=None):
    """Publish feat-<SHA8> images from a pinned checkout, preserving Git refs."""
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

    if shutil.which("docker") is None:
        raise Error("Install docker first; see docs/operations/ci-cd.md")
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

    with log_context(branch=branch, sha=source, image_tag=tag):
        with stage("Publish feature images"), repo.checkout(source) as checkout:
            app, _ = versions(checkout.root)
            images = publish_images(
                checkout.root, registry, IMAGE_PREFIX, app, source, tag, build
            )
        for image in images.values():
            logger.info(
                "Feature image published: %s:%s (%s)",
                image["repository"],
                image["tag"],
                image["digest"],
            )
        return images
