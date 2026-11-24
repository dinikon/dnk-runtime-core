from collections.abc import Iterator
import json
from io import TextIOWrapper
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from dataclasses import asdict
from uuid import UUID
from datetime import datetime
from src.modules.feed_builder.application.feed.service.xml_document import (
    XmlDocumentSection,
)
from src.modules.feed_builder.domain.feed.types import ResolvedFieldValue
from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.application.feed.service.publication_export import (
    csv_cell,
)
from src.modules.feed_builder.domain.feed.types import ExportFormatSettings
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.infrastructure.export_state.serialization.xml import (
    TemporaryXml,
)
from src.modules.feed_builder.infrastructure.feed.serialization.test_csv import (
    TemporaryCsvStorage,
)


class TemporaryRefreshOutput:
    """Временно хранит файл и поток диагностик, выгружая большие результаты на диск."""

    def __init__(
        self,
        settings: ExportFormatSettings,
        fields: tuple[FieldExportSettingsVO, ...],
        *,
        shop: bool = False,
        has_document_sections: bool = False,
        feed_name: str = "",
        as_of: datetime | None = None,
    ) -> None:
        """Открывает независимые временные файлы одного прохода."""
        self.format = settings.format
        if isinstance(settings, CsvExportSettingsVO):
            csv = TemporaryCsvStorage().open(settings)
            if settings.include_header:
                csv.write(tuple(field.name.value for field in fields))
            self._file = csv
        else:
            self._file = TemporaryXml(
                settings,
                fields,
                shop=shop,
                has_document_sections=has_document_sections,
                feed_name=feed_name,
                as_of=as_of,
            )
        self._issues = TextIOWrapper(
            SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b"), encoding="utf-8"
        )

    def write(self, row: tuple[ResolvedFieldValue, ...]) -> None:
        """Сериализует публикацию по формату задачи."""
        if isinstance(self._file, TemporaryXml):
            self._file.write(row)
        else:
            self._file.write(tuple(csv_cell(value) for value in row))

    def document(self, sections: tuple[XmlDocumentSection, ...]) -> None:
        """Передаёт секции вывода выбранному сериализатору XML."""
        if isinstance(self._file, TemporaryXml):
            self._file.document(sections)

    def issue(self, item: FeedExportIssueDTO) -> None:
        """Добавляет диагностику в порядке обработки."""
        self._issues.write(
            json.dumps(asdict(item), ensure_ascii=False, default=str) + "\n"
        )

    def upload_source(self) -> tuple[BinaryIO, int]:
        """Возвращает готовый источник для Files."""
        return self._file.upload_source()

    def issues(self) -> Iterator[FeedExportIssueDTO]:
        """Читает диагностики ограниченным потоком."""
        self._issues.seek(0)
        for line in self._issues:
            item = json.loads(line)
            for key in ("publication_id", "field_id", "rule_id"):
                if item[key] is not None:
                    item[key] = UUID(item[key])
            item["path"] = tuple(item["path"])
            yield FeedExportIssueDTO(**item)

    def close(self) -> None:
        """Освобождает временные файлы в любом исходе."""
        self._file.close()
        self._issues.close()
