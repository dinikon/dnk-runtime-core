from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RegisterSystemStorageResultDTO:
    """Результат сценария register_system_storage; не является доменным агрегатом."""

    provider_id: UUID
    bucket_id: UUID
