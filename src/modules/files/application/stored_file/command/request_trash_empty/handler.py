from src.modules.files.application.stored_file.command.request_trash_empty.command import (
    RequestTrashEmptyCommand,
)
from src.modules.files.application.stored_file.command.request_trash_empty.dto import (
    RequestTrashEmptyResultDTO,
)
from src.modules.files.application.stored_file.port.purge_queue import (
    FilePurgeQueueProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class RequestTrashEmptyHandler:
    """Сохраняет фоновый проход корзины в транзакции внешнего UoW."""

    def __init__(
        self,
        queue: FilePurgeQueueProtocol,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает очередь общей транзакции, доверенные часы и генератор UUID."""
        self._queue, self._clock, self._uuids = queue, clock, uuids

    async def execute(
        self, command: RequestTrashEmptyCommand
    ) -> RequestTrashEmptyResultDTO:
        """Фиксирует неизменный cutoff; новые попадания в корзину не включаются в проход."""
        cutoff = self._clock.now()
        job_id = self._uuids.new()
        await self._queue.schedule_empty(command.tenant_id, job_id, cutoff)
        return RequestTrashEmptyResultDTO(job_id, cutoff)
