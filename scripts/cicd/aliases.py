"""Move channel pointers only while the publication matches remote HEAD."""

from .common import Error
from .observability import logger
from .registry import Registry, wait_for_manifest


def current_publication(repo, record):
    """Refresh remote refs before checking eligibility to move channel aliases."""
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
            logger.info("A newer branch HEAD exists; leaving floating tags unchanged")
            return False
        ref = repository + ":" + tag
        if registry.manifest(ref) is None or registry.digest(ref) != digest:
            registry.alias(repository, digest, tag)
        wait_for_manifest(registry, ref, digest=digest)
        logger.info("Published alias: %s (%s)", ref, digest)
    return True
