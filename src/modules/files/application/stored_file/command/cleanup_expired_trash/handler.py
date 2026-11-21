from src.modules.files.application.stored_file.port.usage import FileUsagePort
from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.dto import (
    CleanupExpiredTrashResultDTO,
)
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.port.purge_queue import (
    FilePurgeQueueProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.domain.error import FileNotFoundError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CleanupExpiredTrashHandler:
    """Ставит истёкшую корзину и остановившиеся удаления в durable очередь."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        queries: StoredFileQueryRepositoryProtocol,
        queue: FilePurgeQueueProtocol,
        uuids: UUIdGeneratorProtocol,
        usage: FileUsagePort,
    ) -> None:
        """Принимает порты одной транзакции и генератор новых идентификаторов."""
        self._usage = usage
        self._files, self._queries, self._queue, self._uuids = (
            files,
            queries,
            queue,
            uuids,
        )

    async def execute(
        self, command: CleanupExpiredTrashCommand
    ) -> CleanupExpiredTrashResultDTO:
        """Блокирует кандидатов по порядку ID и повторно проверяет актуальное состояние."""
        if type(command.batch_size) is not int or not 1 <= command.batch_size <= 100:
            raise ValueError("Trash cleanup batch must contain 1–100 files.")
        if command.now.utcoffset() is None:
            raise ValueError("Trash cleanup cutoff must be timezone-aware.")
        candidates = await self._queries.cleanup_candidates(command)
        files = []
        for candidate in candidates:
            try:
                files.append(
                    await self._files.get_for_update(
                        EntityIdVO.from_value(candidate.file_id)
                    )
                )
            except FileNotFoundError:
                continue
        job_ids = tuple(
            file.purge_job_id.uuid
            for file in files
            if file.status == StoredFileStatus.PURGING
        )
        stopped = await self._queue.terminal_or_missing(command.tenant_id, job_ids)
        used = set(
            await self._usage.used(
                command.tenant_id, tuple(file.id.uuid for file in files)
            )
        )
        queued, requeued = 0, 0
        for file in files:
            if file.id.uuid in used:
                continue
            if file.status == StoredFileStatus.TRASHED:
                job_id = EntityIdVO.from_value(self._uuids.new())
                try:
                    file.request_expired_purge(command.now, job_id)
                except FileStateConflictError:
                    # Между чтением кандидата и lock файл могли восстановить и удалить заново.
                    continue
                queued += 1
            elif (
                file.status == StoredFileStatus.PURGING
                and file.purge_job_id.uuid in stopped
            ):
                job_id = EntityIdVO.from_value(self._uuids.new())
                file.replace_purge_job(job_id)
                requeued += 1
            else:
                continue
            await self._files.save(file)
            await self._queue.schedule(
                command.tenant_id, file.id.uuid, job_id.uuid, command.now
            )
        cursor = (
            candidates[-1].file_id if len(candidates) == command.batch_size else None
        )
        return CleanupExpiredTrashResultDTO(queued, requeued, cursor)
