from src.modules.channels.application.batch_export.query.get_batch_export_overview.dto import (
    ExportScheduleDTO,
)
from src.modules.channels.application.batch_export.contracts import (
    BatchExportSummaryDTO,
)
from src.modules.channels.application.batch_export.query.get_batch_export.dto import (
    BatchExportDetailDTO,
)
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExportFeedDTO:
    """Передаёт только метаданные готового неизменяемого артефакта."""

    file_id: UUID
    expires_at: datetime
    digest: str
    size: int


@dataclass(frozen=True, slots=True)
class BatchExportChannelScopeDTO:
    """Передаёт только данные маршрутизации overview без восстановления корня."""

    connection_id: UUID
    platform_kind: str
    outbound_enabled: bool


class BatchExportQueries(Protocol):
    """Читает проекции независимо от восстановления Domain."""

    async def scope(self, run_id: UUID) -> UUID:
        """Разрешает run ID в канал для порядка блокировок."""
        ...

    async def detail(
        self, run_id: UUID, offset: int, limit: int
    ) -> BatchExportDetailDTO:
        """Возвращает страницу результатов одного пакета."""
        ...

    async def recent(self, channel_id: UUID) -> tuple[BatchExportSummaryDTO, ...]:
        """Возвращает последние двадцать операций канала."""
        ...

    async def eligibility(self, connection_id: UUID) -> tuple[int, int]:
        """Считает активные связи и явно разрешённые представления."""
        ...

    async def feed(self, run_id: UUID) -> ExportFeedDTO:
        """Читает доступный артефакт без восстановления Domain."""
        ...

    async def current_job(self, run_id: UUID) -> UUID | None:
        """Возвращает ID текущего durable intent без доступа к чужим SQL таблицам."""
        ...

    async def channel_scope(self, channel_id: UUID) -> BatchExportChannelScopeDTO:
        """Читает область capabilities и счётчиков канала."""
        ...

    async def schedule(self, channel_id: UUID) -> ExportScheduleDTO:
        """Читает policy как query projection без восстановления агрегата."""
        ...
