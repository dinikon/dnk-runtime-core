"""Результат сценария VerifyConnection."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerifyConnectionDTO:
    """Возвращает идентификатор и актуальную ревизию сохранённого канала."""

    id: UUID
    revision: int
    verification_job_id: UUID
