from uuid import uuid5
from src.modules.channels.application.publication_import.port.jobs import (
    PublicationImportJobsPort,
)
from dataclasses import replace
from src.modules.channels.application.publication_import.query.get_publication_import.query import (
    GetPublicationImportQuery,
)
from src.modules.channels.application.publication_import.query.get_publication_import.dto import (
    GetPublicationImportResultDTO,
)
from src.modules.channels.application.publication_import.port.query_repository import (
    PublicationImportQueryRepositoryProtocol,
)
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.shared.domain.time.clock_port import ClockPort


class GetPublicationImportHandler:
    """Возвращает read-проекцию только владельцу подготовки."""

    def __init__(
        self,
        imports: PublicationImportQueryRepositoryProtocol,
        clock: ClockPort,
        jobs: PublicationImportJobsPort,
    ) -> None:
        """Получает порт проекции и доверенные часы."""
        self.imports, self.clock, self.jobs = imports, clock, jobs

    async def execute(
        self, query: GetPublicationImportQuery
    ) -> GetPublicationImportResultDTO:
        """Отражает истечение срока без изменений в GET и без запуска внешних запросов."""
        result = await self.imports.get(query.preparation_id)
        if result.actor_id != query.actor_id:
            raise ChannelsNotFoundError("import_preparation_not_found")
        if self.clock.now() >= result.expires_at and result.status != "consumed":
            return replace(result, status="expired")
        if result.status in (
            "queued",
            "reading",
            "images",
        ) and not await self.jobs.is_recoverable(
            query.tenant_id,
            uuid5(result.preparation_id, "step:" + str(result.sequence)),
        ):
            return replace(
                result, status="error", error_code="import_worker_interrupted"
            )
        return result
