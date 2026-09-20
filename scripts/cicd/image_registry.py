"""Read image identities with Docker Buildx and its existing registry credentials."""

import json
import re

from .common import Error, run


class DockerImageRegistry:
    """Provide image manifest/digest lookups without an ORAS installation."""

    def __init__(self):
        self._digests = {}

    def manifest(self, ref):
        """Read annotations and digest together; never cache a missing manifest."""
        self._digests.pop(ref, None)
        result = run(
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            "--format",
            "{{json .Manifest}}",
            ref,
            check=False,
        )
        if result.returncode:
            message = result.stderr.lower()
            access_error = any(
                text in message
                for text in (
                    "unauthorized",
                    "forbidden",
                    "denied",
                    "authentication",
                    "failed to authorize",
                    "credentials",
                )
            ) or bool(re.search(r"\b(?:401|403)\b", message))
            missing = (
                message.strip().endswith(ref.lower() + ": not found")
                or "manifest unknown" in message
                or "manifest_unknown" in message
            )
            if missing and not access_error:
                return None
            raise Error(f"Registry lookup failed for {ref}: " + result.stderr)
        try:
            manifest = json.loads(result.stdout)
            digest = manifest["digest"]
            if not isinstance(digest, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", digest
            ):
                raise ValueError("invalid image digest")
        except (ValueError, KeyError, TypeError) as error:
            raise Error(
                f"Docker Buildx returned an invalid manifest for {ref}"
            ) from error
        self._digests[ref] = digest
        return manifest

    def digest(self, ref):
        """Return the digest of the same manifest whose annotations were checked."""
        if ref not in self._digests and self.manifest(ref) is None:
            raise Error(f"Image manifest is missing: {ref}")
        return self._digests[ref]
