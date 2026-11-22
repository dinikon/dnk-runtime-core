from src.modules.feed_builder.application.feed.query.preview_feed.dto import (
    PreviewColumnDTO,
    PreviewFeedResultDTO,
    PreviewIssueDTO,
    PreviewRowDTO,
)
from src.modules.feed_builder.application.feed.query.preview_feed.query import (
    PreviewFeedQuery,
)
from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportService,
    csv_cell,
)

PREVIEW_LIMIT = 20


class PreviewFeedHandler:
    """Вычисляет первые двадцать включённых публикаций рабочей схемы."""

    def __init__(self, export: PublicationExportService) -> None:
        """Использует общий сервис построения экспортных записей."""
        self._export = export

    async def execute(self, query: PreviewFeedQuery) -> PreviewFeedResultDTO:
        """Возвращает значения и ошибки каждой строки образца."""
        context = await self._export.prepare(query.feed_id, query.expected_version)
        total = await self._export.count_enabled(query.feed_id)
        records = ()
        if context.exported_fields and total:
            items = await self._export.read_enabled(query.feed_id, PREVIEW_LIMIT)
            records = await self._export.resolve(context, items)
        return PreviewFeedResultDTO(
            context.feed.id,
            context.feed.version,
            context.as_of,
            total,
            tuple(
                PreviewColumnDTO(field.id.uuid, field.export.name.value)
                for field in context.exported_fields
            ),
            tuple(
                PreviewRowDTO(
                    row.publication_id,
                    row.catalog_item_id,
                    row.catalog_variant_id,
                    row.sku,
                    tuple(csv_cell(value) for value in row.values),
                    tuple(
                        PreviewIssueDTO(
                            issue.field_id,
                            issue.code,
                            issue.message,
                            issue.path,
                            issue.rule_id,
                        )
                        for issue in row.issues
                    ),
                    row.readiness,
                )
                for row in records
            ),
        )
