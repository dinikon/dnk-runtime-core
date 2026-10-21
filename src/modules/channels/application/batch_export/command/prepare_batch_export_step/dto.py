from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO


@dataclass(frozen=True, slots=True)
class PreparedBatchExportStepDTO:
    """Передаёт минимум данных сетевого шага после завершения SQL-транзакции."""

    run_id: UUID
    sequence: int
    mode: str
    connection_id: UUID
    platform_kind: str
    settings: ResourceSettingsDTO
    ciphertext: str = field(repr=False)
    expires_at: datetime
    item: ExportItemVO | None = None
    cursor: str | None = None
    remote_id: str | None = None
    feed_url: str | None = field(default=None, repr=False)
