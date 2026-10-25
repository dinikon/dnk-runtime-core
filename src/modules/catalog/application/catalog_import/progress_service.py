from uuid import UUID
from src.modules.catalog.application.catalog_import.contracts import (
    ImportRowsPort,
    ImportRowResult,
)
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ImportProgressService:
    """Координирует технические этапы через доменные переходы общей транзакции."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        rows: ImportRowsPort,
        clock: ClockPort,
    ) -> None:
        """Принимает порты текущего внешнего UoW без инфраструктурных типов."""
        self.repository, self.rows, self.clock = repository, rows, clock

    async def attach_source(self, identifier: UUID, file_id: UUID) -> None:
        """Сохраняет единственную ссылку на подтверждённый снимок."""
        entity = await self.repository.get(EntityIdVO(identifier), lock=True)
        entity.attach_source(EntityIdVO(file_id), self.clock.now())
        await self.repository.save(entity)

    async def fail(self, identifier: UUID, message: str) -> None:
        """Закрывает окончательно отклонённый или технически исчерпанный запуск."""
        entity = await self.repository.get(EntityIdVO(identifier), lock=True)
        entity.fail(message, self.clock.now())
        await self.repository.save(entity)

    async def stop(self, identifier: UUID) -> None:
        """Подтверждает остановку на границе SQL-фазы."""
        entity = await self.repository.get(EntityIdVO(identifier), lock=True)
        entity.stop(self.clock.now())
        await self.repository.save(entity)

    async def record_error(
        self,
        identifier: UUID,
        number: int,
        sku: str | None,
        message: str,
        warnings: tuple[str, ...],
    ) -> bool:
        """После rollback учитывает ошибку только ещё не обработанной позиции."""
        entity = await self.repository.get(EntityIdVO(identifier), lock=True)
        if entity.status == "cancelling":
            entity.stop(self.clock.now())
            await self.repository.save(entity)
            return False
        pending = await self.rows.next_row(identifier)
        if pending is None or pending.number != number:
            return False
        entity.begin(self.clock.now())
        await self.rows.finish(
            identifier,
            ImportRowResult(
                number,
                "errors",
                sku[:255] if sku else None,
                errors=(message[:1000],),
                warnings=warnings,
            ),
        )
        entity.record("errors", len(warnings), self.clock.now())
        await self.repository.save(entity)
        return True
