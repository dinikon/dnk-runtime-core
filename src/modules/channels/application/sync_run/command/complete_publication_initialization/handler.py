from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.sync_run.command.complete_publication_initialization.command import (
    CompletePublicationInitializationCommand,
)


class CompletePublicationInitializationHandler:
    """Координирует конкретный шаг complete_publication_initialization."""

    def __init__(self, runs: SyncRunRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.runs = runs
        self.clock = clock

    async def execute(self, command: CompletePublicationInitializationCommand) -> None:
        """Сохраняет результат шага без HTTP и самостоятельного commit."""
        run = await self.runs.get(EntityIdVO.from_value(command.run_id))
        if run.status == "running" and run.sequence == command.sequence:
            run.finish(self.clock.now())
            await self.runs.save(run)
