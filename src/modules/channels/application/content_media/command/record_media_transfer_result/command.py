from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RecordMediaTransferResultCommand:
    """Конкретное намерение record_media_transfer_result из доверенного контекста."""

    channel_id: UUID
    config_revision: int
    identity_namespace: str
    identity_key: str
    operation_id: UUID
    media_id: UUID
    expected_revision: int
    remote_id: str | None
    error: str | None
    uncertain: bool
