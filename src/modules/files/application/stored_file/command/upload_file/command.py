from dataclasses import dataclass
from uuid import UUID
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class UploadFileCommand:
    """Вход сценария upload_file в доверенном tenant-контексте."""

    tenant_id: UUID
    source: BinaryIO
    size_bytes: int
    name: str
    content_type: str
    bucket_id: UUID | None = None
