from dataclasses import replace
from uuid import UUID

from src.modules.channels.application.channel.port.jobs import VerificationJobs
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.channel.port.query_repository import (
    ChannelReadRow,
)
from src.modules.channels.application.channel.port.query_repository import (
    ConnectionConfigReadRow,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.enum.verification_status import (
    VerificationStatus,
)


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
        enriched = []
        for row in rows:
            platform = self.platforms.get(row.platform_kind)
            config = platform.validate(
                ConnectionConfigVO.create(
                    version=row.config.version,
                    endpoint=row.config.endpoint,
                    settings=row.config.settings,
                ),
                None,
            ).config
            capabilities = (
                platform.manifest.supported_capabilities
                if row.verification.status is VerificationStatus.VERIFIED
                else ("verify_connection",)
            )
            capabilities = tuple(
                capability
                for capability in capabilities
                if capability != "write_stock" or row.allow_stock_export
            )
            enriched.append(
                replace(
                    row,
                    config=ConnectionConfigReadRow(
                        config.version,
                        config.endpoint,
                        {
                            **config.settings,
                            "stock_sync": {"allow_export": row.allow_stock_export},
                        },
                    ),
                    recovery_required=row.verification.status
                    is VerificationStatus.PENDING
                    and row.verification.job_id in inactive,
                    available_capabilities=capabilities,
                )
            )
        return tuple(enriched)
