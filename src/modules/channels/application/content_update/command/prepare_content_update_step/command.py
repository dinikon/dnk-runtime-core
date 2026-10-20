from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareContentUpdateStepCommand:
    """Адресует один durable шаг без живой request-scoped сессии."""

    tenant_id: UUID
    run_id: UUID
    sequence: int
