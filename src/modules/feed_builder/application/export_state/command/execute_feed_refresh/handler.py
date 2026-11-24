from uuid import UUID
from src.modules.feed_builder.application.export_state.command.execute_feed_refresh.command import (
    ExecuteFeedRefreshCommand,
)
from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.application.export_state.port.batch_reader import (
    FeedRefreshBatchReaderPort,
)
from src.modules.feed_builder.application.export_state.port.refresh_output import (
    FeedRefreshOutputPort,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCursor,
)
from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)


class ExecuteFeedRefreshHandler:
    """Обходит включённые публикации и формирует полный отчёт проверки."""

    def __init__(self, reader: FeedRefreshBatchReaderPort) -> None:
        """Принимает публичный порт пакетного чтения."""
        self._reader = reader

    async def execute(
        self,
        command: ExecuteFeedRefreshCommand,
        output: FeedRefreshOutputPort,
    ) -> ExportCountsVO:
        """Считает каждую позицию ровно один раз и продолжает после ошибок данных."""
        valid = warnings = rejected = 0
        cursor: PublicationCursor | None = None
        used: dict[UUID, set[UUID]] = {}
        while True:
            records, cursor = await self._reader.read_batch(
                command.context, cursor, 100
            )
            for row in records:
                for issue in row.issues:
                    output.issue(
                        FeedExportIssueDTO(
                            row.publication_id,
                            "ERROR",
                            issue.code,
                            issue.message,
                            row.sku,
                            issue.field_id,
                            issue.rule_id,
                            issue.path,
                        )
                    )
                for issue in row.warnings:
                    output.issue(
                        FeedExportIssueDTO(
                            row.publication_id,
                            "WARNING",
                            issue.code,
                            issue.message,
                            row.sku,
                            issue.field_id,
                            issue.rule_id,
                            issue.path,
                        )
                    )
                if row.issues:
                    rejected += 1
                    continue
                if row.warnings:
                    warnings += 1
                else:
                    valid += 1
                output.write(row.values)
                for assignment in row.categories:
                    used.setdefault(assignment.field_id, set()).add(assignment.node_id)
            if cursor is None:
                break
        sections = tuple(
            section
            for resolver in command.context.category_fields
            if (section := resolver.document(used.get(resolver.field.id.uuid, set())))
            is not None
        )
        if sections:
            output.document(sections)
        return ExportCountsVO(valid + warnings + rejected, valid, warnings, rejected)
