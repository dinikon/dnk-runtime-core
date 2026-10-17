from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.application.stored_file.command.trash_file.dto import (
    TrashFileResultDTO,
)


class TrashFileHandler:
    """Переносит файл в корзину под lock внешнего UoW без изменения объекта storage."""

    def __init__(self, files: StoredFileRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает write repository и доверенный источник времени."""
        self._files, self._clock = files, clock

    async def execute(self, command: TrashFileCommand) -> TrashFileResultDTO:
        """Проверяет переход в Domain после получения lock и сохраняет исходные сроки."""
        file = await self._files.get_for_update(EntityIdVO.from_value(command.file_id))
        file.move_to_trash(EntityIdVO.from_value(command.actor_id), self._clock.now())
        await self._files.save(file)
        assert file.deleted_at is not None and file.purge_after is not None
        return TrashFileResultDTO(file.id.uuid, file.deleted_at, file.purge_after)
