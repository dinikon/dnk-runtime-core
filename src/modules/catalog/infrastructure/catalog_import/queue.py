from datetime import timedelta
from uuid import UUID, uuid5
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class ScheduledCatalogImportQueue:
    """Адаптирует общий scheduler к идемпотентным этапам Catalog."""

    def __init__(
        self, tenant_id: UUID, scheduler: ScheduleScheduledJobUseCase, clock: ClockPort
    ) -> None:
        """Получает scheduler той же транзакции, что и агрегат."""
        self.tenant_id, self.scheduler, self.clock = tenant_id, scheduler, clock

    async def schedule(
        self,
        identifier: EntityIdVO,
        version: int,
        cursor: int,
        kind: str,
        delay_seconds: int | None = None,
    ) -> EntityIdVO:
        """Повторная постановка этапа сохраняет его исходный job ID."""
        job_id = uuid5(identifier.uuid, f"{kind}:{version}:{cursor}")
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id=self.tenant_id,
                job_type=f"catalog.import.{kind}",
                payload={
                    "import_id": str(identifier.uuid),
                    "version": version,
                    "cursor": cursor,
                },
                run_at=self.clock.now()
                + timedelta(
                    seconds=(
                        delay_seconds
                        if delay_seconds is not None
                        else 300 if kind == "maintain" else 1
                    )
                ),
                job_id=job_id,
            )
        )
        return EntityIdVO(job_id)
