from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetLeadConversionContextQuery:
    """Подготовка формы без создания результатов."""

    tenant_id: UUID
    lead_id: UUID
