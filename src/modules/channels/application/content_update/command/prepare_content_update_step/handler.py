from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.content_update.command.prepare_content_update_step.command import (
    PrepareContentUpdateStepCommand,
)
from src.modules.channels.application.content_update.command.prepare_content_update_step.dto import (
    PrepareContentUpdateStepResultDTO,
)
from src.modules.channels.application.content_update.access import ContentUpdateAccess
from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
)
from src.modules.channels.application.content_update.texts import plugin_texts
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ReadPublicationDetailsInputDTO,
)
from src.modules.channels.domain.error import ChannelsError, ChannelsConflictError


class PrepareContentUpdateStepHandler:
    """Фиксирует право и intent шага до внешнего вызова."""

    def __init__(self, access: ContentUpdateAccess, clock: ClockPort) -> None:
        """Принимает только порты уже открытого UoW."""
        self.access, self.clock = access, clock

    async def execute(
        self, command: PrepareContentUpdateStepCommand
    ) -> PrepareContentUpdateStepResultDTO | None:
        """Повтор отправленного intent выполняет сверку вместо второго PUT."""
        run, channel = await self.access.locked(command.run_id)
        item = run.current(command.sequence)
        if item is None:
            return None
        try:
            if self.clock.now() >= run.expires_at:
                raise ChannelsConflictError("content_update_expired")
            sending = item.status == "pending"
            await self.access.validate(
                run, channel, command.tenant_id, sending=sending, check_content=sending
            )
        except ChannelsError as error:
            run.invalidate(str(error))
            await self.access.runs.save(run)
            return None
        dispatched = run.dispatch(command.sequence)
        if dispatched is None:
            return None
        item, mode = dispatched
        connection = channel.require_connection()
        request = InspectContentUpdateInputDTO(
            ReadPublicationDetailsInputDTO(
                ResourceSettingsDTO(
                    connection.settings.endpoint, connection.settings.options
                ),
                connection.resource_identity,
                item.resource_type,
                item.external_id,
                item.provider_context,
            ),
            plugin_texts(item.desired),
        )
        await self.access.runs.save(run)
        return PrepareContentUpdateStepResultDTO(
            item.publication_id.uuid,
            connection.id.uuid,
            channel.platform_kind,
            mode,
            request,
            item.observed.digest() if item.observed else None,
            connection.credentials_ciphertext,
        )
