from src.modules.channels.application.external_publication.query.get_publication.query import (
    GetPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    PublicationDetailsDTO,
)
from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationQueryRepositoryProtocol,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.external_publication.error import (
    PublicationNotFoundError,
)


class GetPublicationHandler:
    """Читает проекции сценария get_publication в границах канала."""

    def __init__(
        self,
        repository: PublicationQueryRepositoryProtocol,
        channels: ChannelQueryRepositoryProtocol,
    ) -> None:
        """Принимает порты чтения на общей tenant-сессии."""
        self._repository, self._channels = repository, channels

    async def execute(self, query: GetPublicationQuery) -> PublicationDetailsDTO:
        """Проверяет наличие канала и возвращает конкретный результат чтения."""
        if await self._channels.get(query.channel_id) is None:
            raise ChannelNotFoundError()
        result = await self._repository.get(query.channel_id, query.publication_id)
        if result is None:
            raise PublicationNotFoundError()
        return result
