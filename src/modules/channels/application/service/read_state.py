from dataclasses import replace
from uuid import UUID

from src.modules.channels.application.port.jobs import VerificationJobs
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.port.query_repository import ChannelReadRow
from src.modules.channels.domain.enum.verification_status import VerificationStatus


class ChannelReadState:
    """Дополняет SQL-проекции актуальностью задания и доступными возможностями."""

    def __init__(self, jobs: VerificationJobs, platforms: PlatformRegistry) -> None:
        """Принимает общие порты чтения состояния."""
        self.jobs, self.platforms = jobs, platforms

    async def enrich(
        self, tenant_id: UUID, rows: tuple[ChannelReadRow, ...]
    ) -> tuple[ChannelReadRow, ...]:
        """Проверяет задания страницы одним ограниченным запросом."""
        ids = [
            row.verification.job_id
            for row in rows
            if row.verification.status is VerificationStatus.PENDING
        ]
        inactive = await self.jobs.inactive(tenant_id, ids) if ids else set()
        return tuple(
            replace(
                row,
                recovery_required=row.verification.status is VerificationStatus.PENDING
                and row.verification.job_id in inactive,
                available_capabilities=self.platforms.get(
                    row.platform_kind
                ).manifest.supported_capabilities,
            )
            for row in rows
        )
