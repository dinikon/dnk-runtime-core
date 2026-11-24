from dataclasses import dataclass

from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportContext,
)


@dataclass(frozen=True, slots=True)
class ExecuteFeedRefreshCommand:
    """Передаёт подготовленный контекст текущей задачи расчёта."""

    context: PublicationExportContext
