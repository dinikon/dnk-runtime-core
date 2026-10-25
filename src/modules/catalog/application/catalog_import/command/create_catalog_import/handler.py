from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport
from src.modules.catalog.domain.error import CatalogConflictError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from .command import CreateCatalogImportCommand
from .dto import CreateCatalogImportResultDTO


class CreateCatalogImportHandler:
    """Отдельный сценарий create_catalog_import."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        queue: ImportQueuePort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает порты одного внешнего tenant UoW."""
        self.repository, self.queue, self.clock, self.uuid = (
            repository,
            queue,
            clock,
            uuid,
        )

    async def execute(
        self, command: CreateCatalogImportCommand
    ) -> CreateCatalogImportResultDTO:
        """Создаёт либо возвращает исходный запуск идемпотентного запроса."""
        await self.repository.lock_lane()
        existing = await self.repository.by_key(command.key)
        if existing:
            if existing.fingerprint != command.fingerprint:
                raise CatalogConflictError(
                    "Idempotency-Key уже использован для другого источника."
                )
            return CreateCatalogImportResultDTO(existing.id.uuid, existing.status)
        entity = CatalogImport.create(
            identifier=EntityIdVO(self.uuid.new()),
            actor_id=EntityIdVO(command.actor_id),
            key=command.key,
            fingerprint=command.fingerprint,
            name=command.source_name,
            url=command.source_url,
            file_id=(
                EntityIdVO(command.source_file_id) if command.source_file_id else None
            ),
            configuration=command.configuration,
            now=self.clock.now(),
        )
        job_id = await self.queue.schedule(entity.id, entity.version, 0, "prepare")
        entity.schedule(job_id, self.clock.now())
        await self.repository.save(entity)
        await self.queue.schedule(entity.id, 1, 0, "maintain")
        return CreateCatalogImportResultDTO(entity.id.uuid, entity.status)
