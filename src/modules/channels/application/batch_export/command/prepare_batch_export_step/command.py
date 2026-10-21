from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareBatchExportStepCommand:
    """Описывает единственный разрешённый durable шаг."""

    tenant_id: UUID
    run_id: UUID
    sequence: int
