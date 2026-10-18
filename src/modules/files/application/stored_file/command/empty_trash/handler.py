from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashResultDTO,
)
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.port.purge_queue import (
    FilePurgeQueueProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.error import FileNotFoundError
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class EmptyTrashHandler:
    """Ставит одну порцию текущей корзины на удаление через доменные переходы."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        queries: StoredFileQueryRepositoryProtocol,
        queue: FilePurgeQueueProtocol,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты одной транзакции; не открывает UoW и не выполняет storage I/O."""
        self._files, self._queries, self._queue = files, queries, queue
        self._clock, self._uuids = clock, uuids

    async def execute(self, command: EmptyTrashCommand) -> EmptyTrashResultDTO:
        """Проверяет актуальную корзину под lock, исключая восстановленные и новые удаления."""
        if type(command.batch_size) is not int or not 1 <= command.batch_size <= 100:
            raise ValueError("Empty trash batch must contain 1–100 files.")
        if command.cutoff.utcoffset() is None:
            raise ValueError("Empty trash cutoff must be timezone-aware.")
        candidates = await self._queries.empty_trash_candidates(command)
        queued = 0
        for candidate in candidates:
            try:
                file = await self._files.get_for_update(
                    EntityIdVO.from_value(candidate.file_id)
                )
            except FileNotFoundError:
                continue
            if (
                file.status != StoredFileStatus.TRASHED
                or file.deleted_at > command.cutoff
            ):
                continue
            job_id = EntityIdVO.from_value(self._uuids.new())
            now = self._clock.now()
            file.request_purge(now, job_id)
            await self._files.save(file)
            await self._queue.schedule(
                command.tenant_id, file.id.uuid, job_id.uuid, now
            )
            queued += 1
        cursor = (
            candidates[-1].file_id if len(candidates) == command.batch_size else None
        )
        return EmptyTrashResultDTO(queued, cursor)
