"""OCI registry access, Helm media types and bounded visibility retries."""

import json
import time

from .common import Error, live, run
from .observability import logger

HELM_CONFIG = "application/vnd.cncf.helm.config.v1+json"
HELM_LAYER = "application/vnd.cncf.helm.chart.content.v1.tar+gzip"
PUBLICATION = "io.dnk.publication"
REGISTRY_RETRY_DELAYS = (1, 2, 4, 8, 15, 30)


class Registry:
    """Read OCI artifacts and publish Helm packages through the ORAS CLI."""

    def __init__(self, plain_http=False):
        # Plain HTTP is used only by disposable local-registry integration tests.
        self.flags = ["--plain-http"] if plain_http else []

    def manifest(self, ref):
        """Return None only for missing manifests; surface registry access failures."""
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
        """Resolve an artifact tag to its content digest."""
        return run("oras", "resolve", *self.flags, ref).stdout.strip()

    def alias(self, repository, digest, tag):
        """Point a mutable channel tag at an existing immutable digest."""
        run("oras", "tag", *self.flags, repository + "@" + digest, tag)

    def push_chart(self, repository, archive, config, publication):
        """Push Helm media types and wait until the resulting manifest is visible."""
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
    """Wait for a pushed manifest or a moved alias to expose the expected digest."""
    for number, delay in enumerate((0, *REGISTRY_RETRY_DELAYS), 1):
        if delay:
            logger.info(
                "Waiting for registry manifest %s; retry %s in %ss", ref, number, delay
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
