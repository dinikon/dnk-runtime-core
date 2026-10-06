from src.modules.channels.application.publication_import_run.query.get_publication_import_run.query import (
    GetPublicationImportRunQuery,
)
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.dto import (
    PublicationImportRunDetailsDTO,
)
from src.modules.channels.application.publication_import_run.port.query_repository import (
    PublicationImportQueryRepositoryProtocol,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError


class GetPublicationImportRunHandler:
    """Читает проекции сценария get_publication_import_run в границах канала."""

    def __init__(
        self,
        repository: PublicationImportQueryRepositoryProtocol,
        channels: ChannelQueryRepositoryProtocol,
    ) -> None:
        """Принимает порты чтения на общей tenant-сессии."""
        self._repository, self._channels = repository, channels

    async def execute(
        self, query: GetPublicationImportRunQuery
    ) -> PublicationImportRunDetailsDTO | None:
        """Проверяет наличие канала и возвращает конкретный результат чтения."""
        if await self._channels.get(query.channel_id) is None:
            raise ChannelNotFoundError()
        return await self._repository.get(
            query.tenant_id, query.channel_id, query.run_id
        )
