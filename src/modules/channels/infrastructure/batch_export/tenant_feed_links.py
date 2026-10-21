from datetime import datetime
from uuid import UUID
from src.modules.tenancy.application.tenant_domain.public_hosts import (
    TenantPublicHostsFacade,
)
from src.modules.channels.application.batch_export.port.feed_links import (
    ExportFeedAvailabilityDTO,
)
from src.modules.channels.infrastructure.batch_export.feed_links import ExportFeedLinks


class TenantExportFeedLinks:
    """Адаптирует публичный фасад Tenancy к адресам выгрузок Channels."""

    def __init__(self, hosts: TenantPublicHostsFacade, signer: ExportFeedLinks) -> None:
        """Принимает read-фасад доменов и независимую подпись файла."""
        self.hosts, self.signer = hosts, signer

    async def availability(self, tenant_id: UUID) -> ExportFeedAvailabilityDTO:
        """Для localhost допускает чтение XML, сохраняя запрет внешней отправки."""
        host = await self.hosts.primary_host(tenant_id)
        origin = self.signer.origin(host or "")
        available = bool(origin and self.signer.signing_available)
        return ExportFeedAvailabilityDTO(
            available, available and origin.startswith("https://")
        )

    async def url(self, tenant_id: UUID, run_id: UUID, expires_at: datetime) -> str:
        """Читает основной домен при каждом обращении, включая выполнение worker."""
        host = await self.hosts.primary_host(tenant_id)
        return self.signer.url(host or "", tenant_id, run_id, expires_at)
