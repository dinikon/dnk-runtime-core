from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.application.feed.port.test_csv import TestCsvFile


@dataclass(frozen=True, slots=True)
class TestCsvIssueDTO:
    """Помогает найти публикацию и поле, заблокировавшие скачивание."""

    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    field_id: UUID | None
    field_name: str | None
    code: str
    message: str
    path: tuple[str | int, ...]
    rule_id: UUID | None


@dataclass(frozen=True, slots=True)
class DownloadTestCsvResultDTO:
    """Передаёт имя и готовый файл либо диагностику неуспешной сборки."""

    filename: str
    file: TestCsvFile | None
    issues: tuple[TestCsvIssueDTO, ...] = ()
