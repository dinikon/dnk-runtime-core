from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.channel.command.apply_connection_verification.command import (
    ApplyConnectionVerificationCommand,
)


class ApplyConnectionVerificationHandler:
    """Координирует конкретный шаг apply_connection_verification."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        initialization: InitializationService,
        clock: ClockPort,
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.initialization = initialization
        self.clock = clock

    async def execute(self, command: ApplyConnectionVerificationCommand) -> None:
        """Сохраняет результат шага без HTTP и самостоятельного commit."""
        from uuid import uuid5

        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        connection = channel.require_connection()
        if (
            channel.is_archived
            or connection.is_paused
            or connection.generation != command.generation
            or (connection.verification_job_id != EntityIdVO.from_value(command.job_id))
            or (connection.verification_status != "queued")
        ):
            return
        outcome = command.outcome
        identity, reason = (outcome.identity, outcome.reason_code)
        if identity and await self.channels.identity_in_use(
            channel.platform_kind, identity, connection.id
        ):
            identity, reason = (None, "resource_identity_in_use")
        channel.apply_verification(
            command.generation,
            identity,
            reason,
            outcome.limitations,
            EntityIdVO.from_value(command.actor_id),
            self.clock.now(),
        )
        await self.channels.save(channel)
        if connection.verification_status == "verified":
            await self.initialization.start(
                command.tenant_id,
                channel,
                command.actor_id,
                uuid5(connection.id.uuid, f"initial:{connection.generation}"),
                automatic=True,
            )
