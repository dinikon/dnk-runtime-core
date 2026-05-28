from __future__ import annotations

from dataclasses import dataclass

from src.modules.segmentation.application.segment_version.dsl.error import (
    SegmentVersionDslInvalidRelationPathError,
)


@dataclass(slots=True, frozen=True)
class SegmentVersionDslRelationPathItem:
    source_object: str
    relation_name: str


def parse_segment_version_relation_path_item(
    value: str,
    *,
    path: str,
) -> SegmentVersionDslRelationPathItem:
    """Parse `<source_object>.<relation_name>` relation path item."""
    parts = value.split(".")
    if len(parts) != 2:
        raise SegmentVersionDslInvalidRelationPathError(
            "Relation path item must use <source_object>.<relation_name> format.",
            path=path,
        )
    source_object = parts[0].strip()
    relation_name = parts[1].strip()
    if not source_object or not relation_name:
        raise SegmentVersionDslInvalidRelationPathError(
            "Relation path source object and relation name must not be blank.",
            path=path,
        )
    return SegmentVersionDslRelationPathItem(
        source_object=source_object,
        relation_name=relation_name,
    )


__all__ = [
    "SegmentVersionDslRelationPathItem",
    "parse_segment_version_relation_path_item",
]
