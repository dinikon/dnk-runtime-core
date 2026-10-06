from src.modules.channels.application.external_publication.query.list_publications.query import (
    ListPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    PublicationPageDTO,
)
from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationQueryRepositoryProtocol,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError


class ListPublicationsHandler:
    """Читает проекции сценария list_publications в границах канала."""

    def __init__(
        self,
        repository: PublicationQueryRepositoryProtocol,
        channels: ChannelQueryRepositoryProtocol,
    ) -> None:
        """Принимает порты чтения на общей tenant-сессии."""
        self._repository, self._channels = repository, channels

    async def execute(self, query: ListPublicationsQuery) -> PublicationPageDTO:
        """Проверяет наличие канала и возвращает конкретный результат чтения."""
        if await self._channels.get(query.channel_id) is None:
            raise ChannelNotFoundError()
        return await self._repository.list(query.channel_id, query.offset, query.limit)
