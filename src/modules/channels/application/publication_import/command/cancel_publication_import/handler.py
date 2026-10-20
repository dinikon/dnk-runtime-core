from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.publication_import.command.cancel_publication_import.command import (
    CancelPublicationImportCommand,
)
from src.modules.channels.application.publication_import.command.cancel_publication_import.dto import (
    CancelPublicationImportResultDTO,
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


class CancelPublicationImportHandler:
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
        self, command: CancelPublicationImportCommand
    ) -> CancelPublicationImportResultDTO:
        """Сохраняет доменный переход и соответствующее durable задание."""
        preparation, source = await self.access.locked(
            command.preparation_id, command.actor_id
        )
        now = self.clock.now()
        preparation.cancel(command.expected_revision, now)
        await self.imports.save(preparation)
        await self.jobs.cleanup(command.tenant_id, preparation.id.uuid, now)
        return CancelPublicationImportResultDTO(
            preparation.id.uuid, preparation.revision
        )
