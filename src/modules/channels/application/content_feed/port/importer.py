from typing import Protocol

from src.modules.channels.application.content_feed.contracts import RenderedFeed
from src.modules.channels.application.content_feed.import_contracts import (
    FeedSubmissionResult,
    FeedPollResult,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.content_feed.delivery import (
    FeedPublicationVerificationVO,
)


class FeedImporterPort(Protocol):
    """Явный порт пакета для подготовки, единственного POST и безопасных чтений."""

    async def prepare(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        document: RenderedFeed,
        feed_url: str,
        force_update: bool,
    ) -> bytes:
        """Проверяет весь ассортимент и возвращает конкретный нативный документ."""
        ...

    async def submit(
        self, *, config: ConnectionConfigVO, credentials: bytes, payload: bytes
    ) -> FeedSubmissionResult:
        """Не выполняет автоматических повторов неоднозначного POST."""
        ...

    async def poll(
        self, *, config: ConnectionConfigVO, credentials: bytes, external_id: str
    ) -> FeedPollResult:
        """Читает известный ID, сохраняя неизвестный ответ как отсутствие отчёта."""
        ...

    async def verify(
        self, *, config: ConnectionConfigVO, credentials: bytes, payload: bytes
    ) -> tuple[FeedPublicationVerificationVO, ...]:
        """Сверяет наблюдаемые поля; URL CDN не считается доказательством содержимого файла."""
        ...
