from src.modules.channels.application.product_representation.command.set_publication_export.command import (
    SetPublicationExportCommand,
)
from src.modules.channels.application.product_representation.command.set_publication_export.dto import (
    SetPublicationExportResultDTO,
)
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.domain.product_representation.repository import (
    ProductRepresentationRepositoryProtocol,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SetPublicationExportHandler:
    """Требует явного разрешения на каждой действующей связи подключения."""

    def __init__(
        self,
        access: BatchExportAccess,
        representations: ProductRepresentationRepositoryProtocol,
    ) -> None:
        """Принимает порты владельцев в общей внешней транзакции."""
        self.access, self.representations = access, representations

    async def execute(
        self, command: SetPublicationExportCommand
    ) -> SetPublicationExportResultDTO:
        """Изменяет выбранные корни атомарно с проверкой revision и принадлежности."""
        if not 1 <= len(command.items) <= 100 or len(
            {v.representation_id for v in command.items}
        ) != len(command.items):
            raise ChannelsValidationError("invalid_export_selection")
        channel = await self.access.channels.get(EntityIdVO(command.channel_id))
        self.access.require_capability(channel)
        connection = channel.require_connection()
        revisions = {}
        for ref in sorted(command.items, key=lambda v: str(v.representation_id)):
            item = await self.representations.get(EntityIdVO(ref.representation_id))
            if item.connection_id != connection.id:
                raise ChannelsConflictError("publication_connection_mismatch")
            item.set_export(command.enabled, ref.expected_revision)
            await self.representations.save(item)
            revisions[item.id.uuid] = item.revision
        return SetPublicationExportResultDTO(revisions)
