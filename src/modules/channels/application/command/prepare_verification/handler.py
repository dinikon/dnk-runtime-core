from src.modules.channels.application.command.prepare_verification.command import (
    PrepareVerificationCommand,
)
from src.modules.channels.application.command.prepare_verification.dto import (
    PrepareVerificationDTO,
)
from src.modules.channels.application.port.jobs import VerificationJobs
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PrepareVerificationHandler:
    """Проверяет актуальность задания и получает снимок подключения."""

    def __init__(
        self, repository: ChannelRepositoryProtocol, jobs: VerificationJobs
    ) -> None:
        """Принимает порты короткого UoW worker."""
        self.repository, self.jobs = repository, jobs

    async def execute(
        self, command: PrepareVerificationCommand
    ) -> PrepareVerificationDTO | None:
        """Возвращает None для удалённого либо устаревшего задания."""
        job = command.job
        channel = await self.repository.get(EntityIdVO.from_value(job.channel_id))
        if (
            channel is None
            or channel.connection.id.uuid != job.connection_id
            or not channel.accepts_result(
                job_id=EntityIdVO.from_value(job.job_id),
                config_revision=job.config_revision,
            )
        ):
            return None
        if not await self.jobs.owns(job, command.lock_token):
            return None
        c = channel.connection
        return PrepareVerificationDTO(
            channel.platform_kind, c.config, c.encrypted_credentials
        )
