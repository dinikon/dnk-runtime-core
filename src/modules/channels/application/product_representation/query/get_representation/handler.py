from src.modules.channels.application.product_representation.query.get_representation.query import (
    GetRepresentationQuery,
)
from src.modules.channels.application.product_representation.query.get_representation.dto import (
    GetRepresentationResultDTO,
)
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationReader,
)


class GetRepresentationHandler:
    """Читает DTO редактора через проекции, без Domain Repository."""

    def __init__(self, reader: RepresentationReader) -> None:
        """Получает read-координатор текущего tenant."""
        self._reader = reader

    async def execute(
        self, query: GetRepresentationQuery
    ) -> GetRepresentationResultDTO:
        """Возвращает defaults для группы без сохранённого representation."""
        context = await self._reader.load(
            channel_id=query.channel_id, group_id=query.group_id
        )
        return GetRepresentationResultDTO(
            state=context.state,
            binding_revision=context.binding.revision,
            config_revision=context.channel.config_revision,
            locales=context.locales,
            items=context.binding.items,
        )
