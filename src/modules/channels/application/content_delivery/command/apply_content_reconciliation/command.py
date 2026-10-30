from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.content_delivery.contracts import (
    ContentWorkSnapshot,
    ContentReconciliationResult,
)


@dataclass(frozen=True, slots=True)
class ApplyContentReconciliationCommand:
    """Фиксация результата чтения конкретной неоднозначной попытки."""

    tenant_id: UUID
    snapshot: ContentWorkSnapshot
    lock_token: str
    result: ContentReconciliationResult
