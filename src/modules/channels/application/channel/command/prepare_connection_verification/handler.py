from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.application.channel.command.prepare_connection_verification.command import (
    PrepareConnectionVerificationCommand,
)
from src.modules.channels.application.channel.command.prepare_connection_verification.dto import (
    PrepareConnectionVerificationResultDTO,
)


class PrepareConnectionVerificationHandler:
    """Координирует конкретный шаг prepare_connection_verification."""

    def __init__(self, channels: ChannelRepositoryProtocol) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels

    async def execute(
        self, command: PrepareConnectionVerificationCommand
    ) -> PrepareConnectionVerificationResultDTO | None:
        """Сохраняет результат шага без HTTP и самостоятельного commit."""
        channel = await self.channels.get(
            EntityIdVO.from_value(command.channel_id), for_update=False
        )
        connection = channel.require_connection()
        if (
            channel.is_archived
            or connection.is_paused
            or connection.generation != command.generation
            or (connection.verification_job_id != EntityIdVO.from_value(command.job_id))
            or (connection.verification_status != "queued")
        ):
            return None
        return PrepareConnectionVerificationResultDTO(
            channel.id.uuid,
            connection.id.uuid,
            connection.generation,
            channel.platform_kind,
            ResourceSettingsDTO(
                connection.settings.endpoint,
                connection.settings.options,
            ),
            connection.candidate_ciphertext or connection.credentials_ciphertext,
        )
