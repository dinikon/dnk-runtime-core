from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StageInput:
    """Значения стадии входного прикладного сценария."""

    name: str
    color: str = "neutral"
    id: UUID | None = None
    client_key: str | None = None


@dataclass(frozen=True, slots=True)
class StageProjection:
    """Чистая проекция стадии для прикладных результатов."""

    id: UUID
    name: str
    color: str
    position: int
