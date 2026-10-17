from src.modules.channels.application.publication_import_run.command.prepare_publication_import.command import (
    PreparePublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.command.prepare_publication_import.dto import (
    PreparePublicationImportResultDTO,
)
from src.modules.channels.application.publication_import_run.worker_state import (
    PublicationImportState,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
)
from src.modules.channels.application.channel.port.secret_cipher import SecretCipherPort


class PreparePublicationImportHandler:
    """Готовит параметры чтения вне транзакции и отмечает запуск работающим."""

    def __init__(self, state: PublicationImportState, cipher: SecretCipherPort) -> None:
        """Принимает координацию транзакции и порт раскрытия credentials."""
        self._state, self._cipher = state, cipher

    async def execute(
        self, command: PreparePublicationImportCommand
    ) -> PreparePublicationImportResultDTO | None:
        """Возвращает снимок подключения только действующему владельцу задания."""
        loaded = await self._state.load(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            run_id=command.run_id,
            job_id=command.job_id,
            lock_token=command.lock_token,
        )
        if loaded is None:
            return None
        channel, run = loaded
        await self._state.runs.save(run.start(self._state.clock.now()))
        return PreparePublicationImportResultDTO(
            PublicationSourceConnection(
                channel.kind.value,
                dict(channel.settings.public),
                self._cipher.decrypt(channel.settings.encrypted_secrets),
            ),
            run.checkpoint,
            run.pages,
        )
