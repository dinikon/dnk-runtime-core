from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.error import FileNotFoundError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class LockReadyFileHandler:
    """Сериализует прикрепление файла с его безопасной очисткой."""

    def __init__(self, files: StoredFileRepositoryProtocol) -> None:
        """Принимает репозиторий уже выбранного tenant UoW."""
        self.files = files

    async def execute(self, command: LockReadyFileCommand) -> None:
        """Удерживает блокировку готового файла до commit потребителя."""
        file = await self.files.get_for_update(EntityIdVO(command.file_id))
        if file.status != "ready":
            raise FileNotFoundError("File is not ready.")
