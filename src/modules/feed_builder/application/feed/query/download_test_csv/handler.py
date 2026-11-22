from src.modules.feed_builder.application.feed.export_settings import settings_from_dto
from src.modules.feed_builder.application.feed.port.test_csv import TestCsvStorage
from src.modules.feed_builder.application.feed.query.download_test_csv.dto import (
    DownloadTestCsvResultDTO,
    TestCsvIssueDTO,
)
from src.modules.feed_builder.application.feed.query.download_test_csv.query import (
    DownloadTestCsvQuery,
)
from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportService,
    csv_cell,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCursor,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)

_BATCH_SIZE = 100


class DownloadTestCsvHandler:
    """Собирает пробный CSV и передаёт только полностью проверенный файл."""

    def __init__(
        self, export: PublicationExportService, storage: TestCsvStorage
    ) -> None:
        """Принимает общий расчёт и порт временного хранения."""
        self._export = export
        self._storage = storage

    async def execute(self, query: DownloadTestCsvQuery) -> DownloadTestCsvResultDTO:
        """Обходит весь включённый ассортимент стабильными пакетами."""
        context = await self._export.prepare(query.feed_id, query.expected_version)
        settings = settings_from_dto(context.feed.export_settings).format_settings
        if not isinstance(settings, CsvExportSettingsVO):
            raise InvalidFeedValueError("Пробный CSV доступен для фида с форматом CSV.")
        if not context.exported_fields:
            raise InvalidFeedValueError(
                "В схеме требуется хотя бы одно экспортируемое поле."
            )
        filename = f"{context.feed.code}.csv"
        names = {
            field.id.uuid: field.export.name.value for field in context.schema.fields
        }
        writer = self._storage.open(settings)
        completed = False
        try:
            if settings.include_header:
                writer.write(
                    tuple(field.export.name.value for field in context.exported_fields)
                )
            before: PublicationCursor | None = None
            while items := await self._export.read_enabled(
                query.feed_id, _BATCH_SIZE, before
            ):
                records = await self._export.resolve(context, items)
                issues = tuple(
                    TestCsvIssueDTO(
                        row.publication_id,
                        row.catalog_item_id,
                        row.catalog_variant_id,
                        row.sku,
                        issue.field_id,
                        names.get(issue.field_id) if issue.field_id else None,
                        issue.code,
                        issue.message,
                        issue.path,
                        issue.rule_id,
                    )
                    for row in records
                    for issue in row.issues
                )
                if issues:
                    return DownloadTestCsvResultDTO(filename, None, issues)
                for row in records:
                    writer.write(tuple(csv_cell(value) for value in row.values))
                if len(items) < _BATCH_SIZE:
                    break
                before = items[-1].created_at, items[-1].id
            writer.finish()
            completed = True
            return DownloadTestCsvResultDTO(filename, writer)
        finally:
            if not completed:
                writer.close()
