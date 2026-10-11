from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.dto import (
    CleanupExpiredTrashCandidateDTO,
    CleanupExpiredTrashBacklogDTO,
)
from datetime import datetime
from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashCandidateDTO,
)
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select, ColumnElement

from src.modules.files.application.stored_file.file_category import (
    FileCategory,
    DOCUMENT_MIME_TYPES,
)
from src.modules.files.application.stored_file.port.query_repository import (
    FileReadBucketDTO,
)
from src.modules.files.application.stored_file.query.list_files.query import (
    ListFilesQuery,
)
from src.modules.files.application.stored_file.query.list_files.dto import (
    ListFilesResultDTO,
)
from src.modules.files.application.stored_file.query.list_trashed_files.query import (
    ListTrashedFilesQuery,
)
from src.modules.files.application.stored_file.query.list_trashed_files.dto import (
    ListTrashedFilesResultDTO,
)
from src.modules.files.application.stored_file.query.get_files_overview.query import (
    GetFilesOverviewQuery,
)
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    GetFilesOverviewResultDTO,
)
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel as File,
)
from src.modules.files.infrastructure.persistence.models.bucket import (
    BucketModel as Bucket,
)
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel as Provider,
)
from src.modules.files.infrastructure.stored_file.persistence.query_mapper import (
    StoredFileQueryMapper,
)


class SqlAlchemyStoredFileQueryRepository:
    """Читает готовые проекции файлов из фиксированной tenant-схемы внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию, привязанную к trusted tenant внешней сборкой."""
        self._session = session

    async def empty_trash_candidates(
        self, command: EmptyTrashCommand
    ) -> tuple[EmptyTrashCandidateDTO, ...]:
        """Читает keyset-порцию корзины всех дисков выбранной tenant-схемы."""
        statement = sa.select(File.id).where(
            File.status == "trashed", File.deleted_at <= command.cutoff
        )
        if command.after_id is not None:
            statement = statement.where(File.id > command.after_id)
        rows = (
            await self._session.execute(
                statement.order_by(File.id).limit(command.batch_size)
            )
        ).mappings()
        return tuple(
            StoredFileQueryMapper.to_empty_trash_candidate(row) for row in rows
        )

    async def cleanup_backlog(self, cutoff: datetime) -> CleanupExpiredTrashBacklogDTO:
        """Вычисляет counts/bytes/старейший срок одним SQL без ORM-агрегатов."""
        expired = sa.and_(File.status == "trashed", File.purge_after <= cutoff)
        pending = File.status == "purging"
        statement = sa.select(
            sa.func.count().filter(expired).label("expired_count"),
            sa.func.coalesce(sa.func.sum(File.size_bytes).filter(expired), 0).label(
                "expired_size_bytes"
            ),
            sa.func.min(File.purge_after)
            .filter(File.purge_after <= cutoff)
            .label("oldest_purge_after"),
            sa.func.count().filter(pending).label("pending_count"),
            sa.func.coalesce(sa.func.sum(File.size_bytes).filter(pending), 0).label(
                "pending_size_bytes"
            ),
        ).where(File.status.in_(("trashed", "purging")))
        row = (await self._session.execute(statement)).mappings().one()
        return StoredFileQueryMapper.to_cleanup_backlog(row)

    async def cleanup_candidates(
        self, command: CleanupExpiredTrashCommand
    ) -> tuple[CleanupExpiredTrashCandidateDTO, ...]:
        """Читает keyset-порцию всех дисков без загрузки агрегатов или storage I/O."""
        statement = sa.select(File.id).where(
            sa.or_(
                sa.and_(File.status == "trashed", File.purge_after <= command.now),
                File.status == "purging",
            )
        )
        if command.after_id is not None:
            statement = statement.where(File.id > command.after_id)
        rows = (
            await self._session.execute(
                statement.order_by(File.id).limit(command.batch_size)
            )
        ).mappings()
        return tuple(StoredFileQueryMapper.to_cleanup_candidate(row) for row in rows)

    async def selected_buckets(
        self, bucket_ids: tuple[UUID, ...]
    ) -> tuple[FileReadBucketDTO, ...]:
        """Читает только ID и состояния явно выбранных дисков текущего tenant."""
        rows = (
            await self._session.execute(
                sa.select(Bucket.id, Bucket.status).where(Bucket.id.in_(bucket_ids))
            )
        ).mappings()
        return tuple(StoredFileQueryMapper.to_bucket(row) for row in rows)

    @staticmethod
    def _category_expression() -> ColumnElement[str]:
        """Применяет общую таблицу MIME к SQL-проекциям всех трёх сценариев."""
        mime = sa.func.lower(
            sa.func.trim(sa.func.split_part(File.content_type, ";", 1))
        )
        return sa.case(
            (mime.startswith("image/"), FileCategory.IMAGES.value),
            (mime.startswith("video/"), FileCategory.VIDEOS.value),
            (mime.in_(sorted(DOCUMENT_MIME_TYPES)), FileCategory.DOCUMENTS.value),
            else_=FileCategory.OTHER.value,
        )

    def _list_statement(
        self,
        *,
        search: str,
        bucket_ids: tuple[UUID, ...],
        category: FileCategory | None,
        statuses: tuple[str, ...],
    ) -> Select:
        """Строит общий SQL-фильтр проекций с буквальным поиском имени."""
        category_expression = self._category_expression()
        statement = (
            sa.select(
                File.id.label("file_id"),
                File.bucket_id,
                Bucket.name.label("bucket_name"),
                Bucket.provider_id,
                Provider.name.label("provider_name"),
                File.name,
                File.content_type,
                File.size_bytes,
                File.created_at,
                File.status,
                File.deleted_at,
                File.purge_after,
                File.purge_requested_at,
                category_expression.label("category"),
            )
            .select_from(File)
            .join(Bucket, File.bucket_id == Bucket.id)
            .join(Provider, Bucket.provider_id == Provider.id)
            .where(
                File.status.in_(statuses),
                Bucket.status == "ready",
            )
        )
        if bucket_ids:
            statement = statement.where(File.bucket_id.in_(bucket_ids))
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(File.name.ilike(f"%{escaped}%", escape="\\"))
        if category is not None:
            statement = statement.where(category_expression == category)
        return statement

    async def _page(
        self,
        statement: Select,
        *,
        page: int,
        page_size: int,
        trash: bool,
    ) -> Sequence[Mapping[str, Any]]:
        """Читает total и ограниченную страницу одним statement, включая пустую страницу."""
        total = statement.with_only_columns(
            sa.func.count().label("total"), maintain_column_froms=True
        ).cte("file_total")
        date = File.deleted_at if trash else File.created_at
        offset = min((page - 1) * page_size, 2**63 - 1)
        items = (
            statement.order_by(date.desc(), File.id.desc())
            .limit(page_size)
            .offset(sa.bindparam("file_offset", offset, type_=sa.BigInteger))
            .cte("file_page")
        )
        date_column = items.c.deleted_at if trash else items.c.created_at
        result = await self._session.execute(
            sa.select(total.c.total, *items.c)
            .select_from(total.outerjoin(items, sa.true()))
            .order_by(
                date_column.desc(),
                items.c.file_id.desc(),
            )
        )
        return result.mappings().all()

    async def list_files(self, query: ListFilesQuery) -> ListFilesResultDTO:
        """Возвращает страницу ready-файлов и согласованный total."""
        statement = self._list_statement(
            search=query.search,
            bucket_ids=query.bucket_ids,
            category=query.category,
            statuses=("ready",),
        )
        rows = await self._page(
            statement, page=query.page, page_size=query.page_size, trash=False
        )
        return ListFilesResultDTO(
            items=tuple(
                StoredFileQueryMapper.to_list_item(row)
                for row in rows
                if row["file_id"] is not None
            ),
            total=rows[0]["total"],
            page=query.page,
            page_size=query.page_size,
        )

    async def list_trashed_files(
        self, query: ListTrashedFilesQuery
    ) -> ListTrashedFilesResultDTO:
        """Возвращает страницу trashed/purging с метаданными корзины."""
        statement = self._list_statement(
            search=query.search,
            bucket_ids=query.bucket_ids,
            category=query.category,
            statuses=("trashed", "purging"),
        )
        rows = await self._page(
            statement, page=query.page, page_size=query.page_size, trash=True
        )
        return ListTrashedFilesResultDTO(
            items=tuple(
                StoredFileQueryMapper.to_trash_item(row)
                for row in rows
                if row["file_id"] is not None
            ),
            total=rows[0]["total"],
            page=query.page,
            page_size=query.page_size,
        )

    async def get_files_overview(
        self, query: GetFilesOverviewQuery
    ) -> GetFilesOverviewResultDTO:
        """Считает готовые файлы, всю корзину и её purging-часть одним снимком."""
        base_statement = (
            sa.select(
                File.status,
                File.size_bytes,
                self._category_expression().label("category"),
            )
            .select_from(File)
            .join(Bucket, File.bucket_id == Bucket.id)
            .where(Bucket.status == "ready")
        )
        if query.bucket_ids:
            base_statement = base_statement.where(File.bucket_id.in_(query.bucket_ids))
        base = base_statement.cte("file_overview_source")
        totals_columns = []
        for prefix, statuses in (
            ("active", ("ready",)),
            ("trashed", ("trashed", "purging")),
            ("pending_purge", ("purging",)),
        ):
            condition = base.c.status.in_(statuses)
            totals_columns.extend(
                (
                    sa.func.count().filter(condition).label(prefix + "_count"),
                    sa.func.coalesce(
                        sa.func.sum(base.c.size_bytes).filter(condition), 0
                    ).label(prefix + "_size_bytes"),
                )
            )
        totals = (
            sa.select(*totals_columns).select_from(base).cte("file_overview_totals")
        )
        counts = (
            sa.select(
                base.c.category,
                sa.func.count().label("files_count"),
                sa.func.sum(base.c.size_bytes).label("size_bytes"),
            )
            .where(base.c.status == "ready")
            .group_by(base.c.category)
            .cte("file_category_counts")
        )
        categories = sa.union_all(
            *(
                sa.select(
                    sa.literal(category.value).label("category"),
                    sa.literal(position).label("position"),
                )
                for position, category in enumerate(FileCategory)
            )
        ).cte("file_categories")
        rows = (
            (
                await self._session.execute(
                    sa.select(
                        *totals.c,
                        categories.c.category,
                        sa.func.coalesce(counts.c.files_count, 0).label("files_count"),
                        sa.func.coalesce(counts.c.size_bytes, 0).label(
                            "category_size_bytes"
                        ),
                    )
                    .select_from(
                        totals.join(categories, sa.true()).outerjoin(
                            counts, counts.c.category == categories.c.category
                        )
                    )
                    .order_by(categories.c.position)
                )
            )
            .mappings()
            .all()
        )
        return StoredFileQueryMapper.to_overview(rows)
