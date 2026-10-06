from typing import Protocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)

from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)


class PublicationImportRunRepositoryProtocol(Protocol):
    """Хранит жизненный цикл импорта на tenant-сессии."""

    async def get(
        self, run_id: PublicationImportRunIdVO
    ) -> PublicationImportRun | None:
        """Загружает запуск для изменения под блокировкой."""
        ...

    async def active(self, channel_id: ChannelIdVO) -> PublicationImportRun | None:
        """Возвращает единственный незавершённый запуск канала."""
        ...

    async def save(self, run: PublicationImportRun) -> None:
        """Записывает запуск в текущую транзакцию."""
        ...
