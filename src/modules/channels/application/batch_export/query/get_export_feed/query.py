from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetExportFeedQuery:
    """Описывает чтение одного файла после проверки подписи capability."""

    tenant_id: UUID
    run_id: UUID
