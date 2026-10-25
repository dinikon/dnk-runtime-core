from datetime import timedelta
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.domain.catalog_import.concurrency_policy import (
    CatalogImportConcurrencyPolicy,
)
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from .command import ResumeCatalogImportCommand
from .dto import ResumeCatalogImportResultDTO


class ResumeCatalogImportHandler:
    """Планирует остаток остановленного импорта на общей транзакции."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        queue: ImportQueuePort,
        clock: ClockPort,
        source_days: int,
        max_active: int,
    ) -> None:
        """Получает порты одного UoW и срок доступности исходного снимка."""
        self.repository, self.queue, self.clock = repository, queue, clock
        self.source_lifetime = timedelta(days=source_days)
        self.policy = CatalogImportConcurrencyPolicy(max_active)

    async def execute(
        self, command: ResumeCatalogImportCommand
    ) -> ResumeCatalogImportResultDTO:
        """Блокирует tenant, сохраняет поколение и новое задание атомарно."""
        await self.repository.lock_lane()
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        now = self.clock.now()
        if entity.resume(command.generation, now, self.source_lifetime):
            self.policy.ensure_capacity(
                await self.repository.count_executing(entity.id)
            )
            job = await self.queue.schedule(
                entity.id,
                entity.version,
                entity.processed,
                "run",
                generation=entity.generation,
            )
            entity.schedule(job, now)
            await self.repository.save(entity)
            await self.queue.schedule(
                entity.id,
                0,
                int(now.timestamp()),
                "maintain",
                generation=entity.generation,
            )
        return ResumeCatalogImportResultDTO(
            entity.id.uuid, entity.status, entity.generation
        )
