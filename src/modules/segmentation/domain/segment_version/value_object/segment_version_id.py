from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class SegmentVersionIdVO(EntityIdVO):
    """Segment version id."""


__all__ = ["SegmentVersionIdVO"]
