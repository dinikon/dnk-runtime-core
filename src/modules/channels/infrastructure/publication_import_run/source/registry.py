from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
    PublicationSourcePage,
    PublicationSourcePort,
)


class PublicationSourceRegistry:
    """Выбирает адаптер чтения для явно поддержанной платформы."""

    def __init__(self, sources: dict[str, PublicationSourcePort]) -> None:
        """Принимает собранные внешним composition root адаптеры."""
        self._sources = sources

    async def read_page(
        self, connection: PublicationSourceConnection, checkpoint: str
    ) -> PublicationSourcePage:
        """Делегирует чтение выбранному адаптеру без fallback между источниками."""
        source = self._sources.get(connection.kind)
        if source is None:
            raise PublicationSourceError("unsupported_platform")
        return await source.read_page(connection, checkpoint)
