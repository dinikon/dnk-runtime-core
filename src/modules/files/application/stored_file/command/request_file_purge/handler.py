from src.modules.files.application.stored_file.port.usage import FileUsagePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.application.stored_file.port.purge_queue import (
    FilePurgeQueueProtocol,
)
from src.modules.files.application.stored_file.command.request_file_purge.command import (
    RequestFilePurgeCommand,
)


class RequestFilePurgeHandler:
    """Фиксирует запрос purge и job атомарно; физическое удаление выполняет worker."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        queue: FilePurgeQueueProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
        usage: FileUsagePort,
    ) -> None:
        """Принимает порты одной транзакции, часы и генератор job ID."""
        self._usage = usage
        self._files, self._queue = files, queue
        self._clock, self._uuid = clock, uuid_generator

    async def execute(self, command: RequestFilePurgeCommand) -> None:
        """Выполняет доменный переход под lock; повтор не меняет job или даты."""
        file = await self._files.get_for_update(EntityIdVO.from_value(command.file_id))
        file.ensure_unused(
            in_use=bool(await self._usage.used(command.tenant_id, (file.id.uuid,)))
        )
        previous_job = file.purge_job_id
        job = previous_job or EntityIdVO.from_value(self._uuid.new())
        now = self._clock.now()
        file.request_purge(now, job)
        if previous_job is None:
            await self._files.save(file)
            await self._queue.schedule(command.tenant_id, file.id.uuid, job.uuid, now)
