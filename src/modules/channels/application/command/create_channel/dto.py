"""Результат сценария CreateChannel."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateChannelDTO:
    """Возвращает идентификатор и актуальную ревизию сохранённого канала."""

    id: UUID
    revision: int
    verification_job_id: UUID
