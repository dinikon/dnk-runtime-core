from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetFilePreviewQuery:
    """Передаёт ID файла и доверенный tenant для административного предпросмотра."""

    tenant_id: UUID
    file_id: UUID
