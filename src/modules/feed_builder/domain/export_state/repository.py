from typing import Protocol

from src.modules.feed_builder.domain.export_state.aggregate import FeedExportState
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


class FeedExportStateRepositoryProtocol(Protocol):
    """Хранит состояние экспорта в tenant UoW."""

    async def get_for_update(self, feed_id: FeedIdVO) -> FeedExportState:
        """Читает состояние после блокировки Feed."""
        ...

    async def save(self, state: FeedExportState) -> None:
        """Сохраняет состояние в текущей транзакции."""
        ...
