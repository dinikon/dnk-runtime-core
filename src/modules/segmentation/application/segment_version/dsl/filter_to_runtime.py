from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def dump_segment_version_filter_for_runtime(
    filter_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-like copy of DSL filter config for runtime_data adapters."""
    return deepcopy(dict(filter_config))


__all__ = ["dump_segment_version_filter_for_runtime"]
