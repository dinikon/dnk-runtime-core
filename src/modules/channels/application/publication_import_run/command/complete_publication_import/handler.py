from src.modules.channels.application.publication_import_run.command.complete_publication_import.command import (
    CompletePublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.worker_state import (
    PublicationImportState,
)


class CompletePublicationImportHandler:
    """Фиксирует окончательную ошибку с сохранением ранее импортированных страниц."""

    def __init__(self, state: PublicationImportState) -> None:
        """Принимает порты общей транзакции завершения."""
        self._state = state

    async def execute(self, command: CompletePublicationImportCommand) -> None:
        """Завершает только действующий запуск текущего владельца задания."""
        loaded = await self._state.load(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            run_id=command.run_id,
            job_id=command.job_id,
            lock_token=command.lock_token,
        )
        if loaded is not None:
            await self._state.runs.save(
                loaded[1].finish(
                    error_code=command.error_code, now=self._state.clock.now()
                )
            )
