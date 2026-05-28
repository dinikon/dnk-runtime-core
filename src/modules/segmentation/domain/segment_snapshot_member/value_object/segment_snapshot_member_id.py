from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class SegmentSnapshotMemberIdVO(EntityIdVO):
    """Segment snapshot member id."""


__all__ = ["SegmentSnapshotMemberIdVO"]
