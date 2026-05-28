from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.segmentation.application.segment_version.dsl.error import (
    SegmentVersionDslValidationError,
)


def assert_segment_version_filter_mapping(
    filter_config: Mapping[str, Any],
    *,
    path: str,
) -> None:
    """Validate the segment DSL filter field is an object before adapter checks."""
    if not isinstance(filter_config, Mapping):
        raise SegmentVersionDslValidationError(
            "filter must be an object.",
            path=path,
        )


__all__ = ["assert_segment_version_filter_mapping"]
