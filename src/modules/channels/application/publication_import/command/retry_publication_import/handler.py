from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import uuid5
from src.modules.channels.application.publication_import.command.retry_publication_import.command import (
    RetryPublicationImportCommand,
)
from src.modules.channels.application.publication_import.command.retry_publication_import.dto import (
    RetryPublicationImportResultDTO,
)
from src.modules.channels.application.publication_import.access import (
    PublicationImportAccess,
)
from src.modules.channels.application.publication_import.port.jobs import (
    PublicationImportJobsPort,
)
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class RetryPublicationImportHandler:
    """Координирует явное действие пользователя без сетевых вызовов."""

    def __init__(
        self,
        access: PublicationImportAccess,
        imports: PublicationImportRepositoryProtocol,
        jobs: PublicationImportJobsPort,
        clock: ClockPort,
    ) -> None:
        """Получает порты общего UoW."""
        self.access, self.imports, self.jobs, self.clock = access, imports, jobs, clock

    async def execute(
        self, command: RetryPublicationImportCommand
    ) -> RetryPublicationImportResultDTO:
        """Сохраняет доменный переход и соответствующее durable задание."""
        preparation, source = await self.access.locked(
            command.preparation_id, command.actor_id
        )
        now = self.clock.now()
        interrupted = preparation.status in (
            "queued",
            "reading",
            "images",
        ) and not await self.jobs.is_recoverable(
            command.tenant_id,
            uuid5(preparation.id.uuid, "step:" + str(preparation.sequence)),
        )
        preparation.retry(command.expected_revision, now, interrupted=interrupted)
        await self.imports.save(preparation)
        await self.jobs.prepare(
            command.tenant_id, preparation.id.uuid, preparation.sequence, now
        )
        return RetryPublicationImportResultDTO(
            preparation.id.uuid, preparation.revision
        )
