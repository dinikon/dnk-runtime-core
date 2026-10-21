from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeBatchExportCommand:
    """Описывает восстановление шага или чтения неопределённого импорта."""

    tenant_id: UUID
    run_id: UUID
