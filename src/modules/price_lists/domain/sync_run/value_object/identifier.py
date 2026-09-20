from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class SyncRunIdVO(EntityIdVO):
    """Идентификатор sync_run."""


__all__ = ["SyncRunIdVO"]
