from typing import Protocol
from src.modules.feed_builder.application.feed.service.xml_document import (
    XmlDocumentSection,
)
from src.modules.feed_builder.domain.feed.types import ResolvedFieldValue
from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO


class FeedRefreshOutputPort(Protocol):
    """Принимает результат пакетного прохода до публикации."""

    def write(self, row: tuple[ResolvedFieldValue, ...]) -> None:
        """Записывает подготовленные значения одной публикации."""
        ...

    def document(self, sections: tuple[XmlDocumentSection, ...]) -> None:
        """Передаёт готовые секции документа перед публикацией файла."""
        ...

    def issue(self, item: FeedExportIssueDTO) -> None:
        """Добавляет диагностику текущего прохода."""
        ...
