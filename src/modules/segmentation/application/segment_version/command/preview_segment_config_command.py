from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class PreviewSegmentConfigCommand:
    """Command for previewing raw segment version config."""

    tenant_id: EntityIdVO
    config: Mapping[str, Any]
    limit: int = 50
    offset: int = 0
    include_contact_summary: bool = True


__all__ = ["PreviewSegmentConfigCommand"]
