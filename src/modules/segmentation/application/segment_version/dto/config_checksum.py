import hashlib
import json
from collections.abc import Mapping
from typing import Any


def build_segment_config_checksum(config: Mapping[str, Any]) -> str:
    """Builds deterministic SHA-256 checksum for segment version config."""
    canonical = json.dumps(
        dict(config),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["build_segment_config_checksum"]
