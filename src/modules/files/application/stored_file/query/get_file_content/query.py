from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetFileContentQuery:
    """Вход сценария get_file_content в доверенном tenant-контексте."""

    tenant_id: UUID
    file_id: UUID
