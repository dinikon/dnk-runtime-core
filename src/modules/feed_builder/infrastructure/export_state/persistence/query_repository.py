from uuid import UUID

from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.application.export_state.query.dto import (
    ActiveFeedFileDTO,
    FeedExportIssuesPageDTO,
    FeedExportReportDTO,
    FeedExportStateDTO,
    FeedExportTaskDTO,
    PublicFeedFileDTO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.infrastructure.persistence.models.export_state import (
    FeedExportIssueModel as Issue,
    FeedExportStateModel as State,
)
from src.modules.feed_builder.infrastructure.persistence.models.feed import (
    FeedModel as Feed,
)


class SqlAlchemyFeedExportQueryRepository:
    """Читает экспорт без восстановления агрегата и загрузки снимка."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает привязанную к tenant сессию."""
        self._session = session

    async def get(self, feed_id: UUID) -> FeedExportStateDTO | None:
        """Собирает строку фида, одной задачи, отчёта и активного файла."""
        row = (
            await self._session.execute(
                select(
                    Feed.status,
                    Feed.row_version,
                    Feed.public_link_id,
                    Feed.export_settings["format_settings"]["format"].astext.label(
                        "configured_format"
                    ),
                    State.job_status,
                    State.requested_at,
                    State.started_at,
                    State.last_completed_at,
                    State.last_as_of,
                    State.last_validation_policy,
                    State.last_outcome,
                    State.last_reason_code,
                    State.last_is_complete,
                    State.total_items,
                    State.valid_items,
                    State.warning_items,
                    State.rejected_items,
                    State.active_file_id,
                    State.active_format,
                    State.active_as_of,
                    State.active_published_at,
                )
                .outerjoin(State, State.feed_id == Feed.id)
                .where(Feed.id == feed_id)
            )
        ).one_or_none()
        if row is None:
            return None
        visible = (
            row.status in ("ACTIVE", "PAUSED")
            and row.active_file_id is not None
            and row.public_link_id is not None
        )
        return FeedExportStateDTO(
            feed_version=row.row_version,
            can_refresh=row.status in ("DRAFT", "ACTIVE")
            and row.configured_format in (ExportFormat.CSV, ExportFormat.XML),
            can_rotate=visible,
            task=(
                FeedExportTaskDTO(row.job_status, row.requested_at, row.started_at)
                if row.job_status is not None
                else None
            ),
            report=(
                FeedExportReportDTO(
                    row.last_completed_at,
                    row.last_as_of,
                    row.last_validation_policy,
                    row.last_outcome,
                    row.last_reason_code,
                    row.last_is_complete,
                    row.total_items,
                    row.valid_items,
                    row.warning_items,
                    row.rejected_items,
                )
                if row.last_completed_at is not None
                else None
            ),
            active=(
                ActiveFeedFileDTO(
                    row.public_link_id,
                    row.active_format,
                    row.active_as_of,
                    row.active_published_at,
                )
                if visible
                else None
            ),
        )

    async def list_issues(
        self, feed_id: UUID, severity: str | None, limit: int, offset: int
    ) -> FeedExportIssuesPageDTO:
        """Читает страницу и её total из одного снимка последнего отчёта."""
        conditions = [Issue.feed_id == feed_id]
        if severity is not None:
            conditions.append(Issue.severity == severity)
        total = (
            select(func.count().label("total"))
            .select_from(Issue)
            .where(*conditions)
            .cte("export_issue_total")
        )
        page = (
            select(Issue.__table__)
            .where(*conditions)
            .order_by(Issue.id)
            .limit(limit)
            .offset(offset)
            .cte("export_issue_page")
        )
        rows = (
            await self._session.execute(
                select(total.c.total, *page.c)
                .select_from(total.outerjoin(page, true()))
                .order_by(page.c.id)
            )
        ).all()
        return FeedExportIssuesPageDTO(
            tuple(
                FeedExportIssueDTO(
                    row.publication_id,
                    row.severity,
                    row.code,
                    row.message,
                    row.sku,
                    row.field_id,
                    row.rule_id,
                    tuple(row.path),
                )
                for row in rows
                if row.id is not None
            ),
            rows[0].total,
        )

    async def get_public_file(
        self, link_id: UUID, format: ExportFormat
    ) -> PublicFeedFileDTO | None:
        """Находит доступный файл указанного формата внутри tenant."""
        row = (
            await self._session.execute(
                select(State.active_file_id, State.active_published_at)
                .join(Feed, Feed.id == State.feed_id)
                .where(
                    Feed.public_link_id == link_id,
                    Feed.status.in_(("ACTIVE", "PAUSED")),
                    State.active_format == format.value,
                    State.active_file_id.is_not(None),
                )
            )
        ).one_or_none()
        return PublicFeedFileDTO(*row) if row is not None else None

    async def used_file_ids(self, file_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        """Возвращает используемые файлы без блокировок потребителя."""
        if not file_ids:
            return ()
        return tuple(
            await self._session.scalars(
                select(State.active_file_id).where(State.active_file_id.in_(file_ids))
            )
        )
