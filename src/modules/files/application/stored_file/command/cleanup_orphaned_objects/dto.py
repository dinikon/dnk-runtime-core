from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CleanupOrphanedObjectsResultDTO:
    """Результат сценария cleanup_orphaned_objects; не является доменным агрегатом."""

    removed_objects: int
    aborted_uploads: int
