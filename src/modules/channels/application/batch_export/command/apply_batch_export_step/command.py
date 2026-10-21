from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.batch_export.plugin_contract import (
    ExportInspectionDTO,
    ExportIdentityPageDTO,
    ExportPollDTO,
)
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO


@dataclass(frozen=True, slots=True)
class ApplyBatchExportStepCommand:
    """Передаёт только безопасный результат завершённого сетевого шага."""

    tenant_id: UUID
    run_id: UUID
    sequence: int
    mode: str
    item: ExportItemVO | None = None
    inspection: ExportInspectionDTO | None = None
    identities: ExportIdentityPageDTO | None = None
    poll: ExportPollDTO | None = None
    remote_id: str | None = None
    artifact_hash: str | None = None
    artifact_size: int | None = None
    issues: tuple[str, ...] = ()
    error_code: str | None = None
    uncertain: bool = False
