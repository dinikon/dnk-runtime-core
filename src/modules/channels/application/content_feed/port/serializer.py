from typing import Protocol
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.channels.application.content_feed.contracts import (
    FeedOverlay,
    RenderedFeed,
)


class ContentFeedSerializerProtocol(Protocol):
    """Граница нативной сериализации без XML-дерева или моделей платформы в ядре."""

    def validate_settings(self, source: FeedSourceVO) -> FeedSourceVO:
        """Восстанавливает и нормализует конкретные настройки пакета."""
        ...

    def render(
        self,
        *,
        source: bytes,
        settings: FeedSourceVO,
        overlays: tuple[FeedOverlay, ...],
    ) -> RenderedFeed:
        """Накладывает контент и проверяет полный итог до возврата байтов."""
        ...
