from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListSegmentDefinitionsQuery:
    """Query for segment definitions page."""

    tenant_id: EntityIdVO
    limit: int = 50
    offset: int = 0


__all__ = ["ListSegmentDefinitionsQuery"]
