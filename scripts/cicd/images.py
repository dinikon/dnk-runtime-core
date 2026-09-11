"""Build missing images together and validate immutable registry tags."""

import hashlib
import os

from .common import Error, live
from .observability import logger, stage
from .registry import wait_for_manifest


def cache_arguments(targets, environment):
    """Opt in to per-image, per-branch registry caches using existing GHCR access.

    Branch names are hashed to valid tags. Main and develop caches are read-only
    fallbacks; each job writes only its own branch cache, separately from images.
    Cache export failures must not fail an otherwise successful image publication.
    """
    if environment.get("CICD_BUILD_CACHE") != "registry":
        return []
    branch = environment.get("BRANCH")
    if not branch:
        raise Error("BRANCH is required when CICD_BUILD_CACHE=registry")
    branches = list(dict.fromkeys((branch, "main", "develop")))
    arguments = []
    for target in targets:
        repository = environment["REGISTRY_PREFIX"] + "/" + target
        refs = [
            repository + ":buildcache-" + hashlib.sha256(name.encode()).hexdigest()[:16]
            for name in branches
        ]
        logger.info("Build cache: target=%s write=%s", target, refs[0])
        for index, ref in enumerate(refs):
            operator = "=" if index == 0 else "+="
            arguments.extend(
                ["--set", f"{target}.cache-from{operator}type=registry,ref={ref}"]
            )
        arguments.extend(
            [
                "--set",
                f"{target}.cache-to=type=registry,ref={refs[0]},mode=max,ignore-error=true",
            ]
        )
    return arguments


def build_images(root, targets, environment):
    """One Bake invocation lets BuildKit schedule independent images in parallel."""
    logger.info("Building and publishing images: %s", ", ".join(targets))
    live(
        "docker",
        "buildx",
        "bake",
        "-f",
        "docker-bake.hcl",
        *targets,
        *cache_arguments(targets, os.environ | environment),
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
    logger.info("Image ready: %s (%s)", ref, digest)
    return {"repository": repository, "tag": tag, "digest": digest}


def publish_images(root, registry, image_prefix, app, source, tag, builder):
    """Build only missing targets and preserve completed pushes after partial failures."""
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
        logger.info("Checking image: %s/%s:%s", image_prefix, target, tag)
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
            with stage("Build missing images", targets=",".join(missing)):
                builder(root, missing, environment)
        except Error:
            # Each image is already pushed under its final tag. A later attempt
            # reuses either completed image, including one that becomes visible late.
            for target in missing:
                try:
                    collect(target, wait=True)
                except Error as error:
                    logger.warning("Could not recover image %s: %s", target, error)
            raise
        for target in missing:
            image = collect(target, wait=True)
            if image is None:
                raise Error(f"Build completed without publishing image {target}")
            images[target] = image
    return images
