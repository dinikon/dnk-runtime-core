from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog.infrastructure.catalog_category.query_repository import (
    SqlAlchemyCatalogCategoryQueryRepository,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.infrastructure.feed.catalog.category_tree import (
    CatalogCategoryTree,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.calculation_reader import (
    SqlAlchemyCatalogCalculationReader,
)
from src.modules.feed_builder.application.export_state.command.execute_feed_refresh.command import (
    ExecuteFeedRefreshCommand,
)
from src.modules.feed_builder.application.export_state.command.execute_feed_refresh.handler import (
    ExecuteFeedRefreshHandler,
)
from src.modules.feed_builder.application.export_state.file_format import (
    EXPORT_MEDIA_TYPES,
)
from src.modules.feed_builder.application.export_state.service import (
    FinishFeedRefreshService,
)
from src.modules.feed_builder.application.feed.service.publication_export import (
    ExportRecord,
    PublicationExportContext,
    PublicationExportService,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCursor,
)
from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)
from src.modules.feed_builder.domain.export_state.policy.publication import (
    publication_rejection_reason,
)
from src.modules.feed_builder.domain.export_state.value_object.export_snapshot import (
    EXPORT_ENGINE_VERSION,
)
from src.modules.feed_builder.domain.export_state.value_object.export_task import (
    ExportTaskVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.infrastructure.export_state.persistence.issue_writer import (
    SqlAlchemyFeedExportIssueWriter,
)
from src.modules.feed_builder.infrastructure.export_state.persistence.repository import (
    SqlAlchemyFeedExportStateRepository,
)
from src.modules.feed_builder.infrastructure.export_state.serialization.refresh_output import (
    TemporaryRefreshOutput,
)
from src.modules.feed_builder.infrastructure.feed.persistence.query_repository import (
    SqlAlchemyFeedQueryRepository,
)
from src.modules.feed_builder.infrastructure.feed.persistence.repository import (
    SqlAlchemyFeedRepository,
)
from src.modules.feed_builder.infrastructure.publication.catalog.export_values import (
    CatalogExportValues,
)
from src.modules.feed_builder.infrastructure.publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.files.application.stored_file.command.request_file_purge.command import (
    RequestFilePurgeCommand,
)
from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.presentation.access.depends import (
    default_authorization_service,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
    build_scheduled_job_repository,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate


class ExportCatalogDenied(Exception):
    """Сохранённый инициатор больше не может читать исходные данные."""


class _CatalogAccess:
    """Применяет те же ресурсные права Catalog, что и Console."""

    def __init__(
        self, tenant: UUID, actor: UUID, authorization: AuthorizationServiceProtocol
    ) -> None:
        """Принимает доверенного tenant и инициатора из состояния задачи."""
        self.tenant, self.actor, self.authorization = tenant, actor, authorization

    async def ensure_readable(self, identifiers: tuple[UUID, ...]) -> None:
        """Проверяет новые ресурсные ID текущего пакета."""
        for identifier in identifiers:
            if not await self.authorization.can(
                user_id=self.actor,
                tenant_id=self.tenant,
                action="catalog.item.read",
                resource_type="catalog.item",
                resource_id=identifier,
            ):
                raise ExportCatalogDenied


class _Runtime:
    """Собирает короткие tenant UoW для фаз ScheduledJob."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        tenant: UUID,
        clock: ClockPort,
        naming: TenantSchemaNaming,
    ) -> None:
        """Получает доверенный tenant из очереди и worker factory."""
        self.sessions, self.tenant, self.clock, self.naming = (
            sessions,
            tenant,
            clock,
            naming,
        )

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Открывает UoW на привязанном tenant-соединении."""
        async with TenantGate(self.sessions).hold(self.tenant) as connection:
            await bind_tenant_schema(connection, self.tenant, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow.session

    async def fence(self, session: AsyncSession, job: ScheduledJob) -> None:
        """Проверяет владение очередью в той же транзакции, что и изменение."""
        if not job.lock_token or not await build_scheduled_job_repository(
            session
        ).owns_current_lease(
            job_id=job.id,
            tenant_id=self.tenant,
            lock_token=job.lock_token,
            for_update=True,
        ):
            raise ScheduledJobDeferred("Feed export lease expired.")

    def finish(self, session: AsyncSession) -> FinishFeedRefreshService:
        """Собирает сервис завершения на текущей сессии."""
        ids = UUID7Generator()
        return FinishFeedRefreshService(
            SqlAlchemyFeedExportStateRepository(session),
            SqlAlchemyFeedRepository(session),
            SqlAlchemyFeedExportIssueWriter(session, ids),
            build_schedule_scheduled_job_use_case(session=session, clock=self.clock),
            self.clock,
            ids,
        )


class _BatchReader:
    """Переиспользует общий PublicationResolver с отдельным UoW на пакет."""

    def __init__(
        self, runtime: _Runtime, feed_id: FeedIdVO, access: _CatalogAccess
    ) -> None:
        """Фиксирует контекст доступа на время выполнения задачи."""
        self.runtime, self.feed_id, self.access = runtime, feed_id, access

    def _export(self, session: AsyncSession) -> PublicationExportService:
        """Подключает read-side Catalog и Feed Builder."""
        return PublicationExportService(
            SqlAlchemyFeedQueryRepository(session),
            SqlAlchemyPublicationQueryRepository(session),
            CatalogExportValues(SqlAlchemyCatalogCalculationReader(session)),
            self.access,
            self.runtime.clock,
            CatalogCategoryTree(SqlAlchemyCatalogCategoryQueryRepository(session)),
        )

    async def prepare(self, task: ExportTaskVO) -> PublicationExportContext:
        """Загружает экспортный контекст именно текущего снимка."""
        assert task.as_of is not None
        async with self.runtime.transaction() as session:
            return await self._export(session).prepare_for_refresh(
                self.feed_id, task.snapshot, task.as_of
            )

    async def read_batch(
        self,
        context: PublicationExportContext,
        cursor: PublicationCursor | None,
        limit: int,
    ) -> tuple[tuple[ExportRecord, ...], PublicationCursor | None]:
        """Читает один пакет и возвращает продолжение для keyset."""
        async with self.runtime.transaction() as session:
            export = self._export(session)
            items = await export.read_enabled(self.feed_id, limit, cursor)
            rows = await export.resolve(context, items)
            return rows, (
                (items[-1].created_at, items[-1].id) if len(items) == limit else None
            )


class FeedExportJobHandler:
    """Выполняет сквозную сборку CSV или XML в существующем jobs worker."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        naming: TenantSchemaNaming,
        authorization: AuthorizationServiceProtocol = default_authorization_service,
        clock: ClockPort | None = None,
    ) -> None:
        """Принимает worker factory и общий контекст авторизации."""
        self._sessions, self._authorization = sessions, authorization
        self._clock = clock or UtcClock()
        self._naming = naming

    async def handle(self, job: ScheduledJob) -> None:
        """Начинает незавершённую задачу, собирает файл и фиксирует результат."""
        if job.tenant_id is None:
            raise ValueError("Feed export requires tenant.")
        feed_id = FeedIdVO(UUID(job.payload["feed_id"]))
        runtime = _Runtime(self._sessions, job.tenant_id, self._clock, self._naming)
        async with runtime.transaction() as session:
            await SqlAlchemyFeedRepository(session).get_for_update(feed_id)
            states = SqlAlchemyFeedExportStateRepository(session)
            state = await states.get_for_update(feed_id)
            if state.task is None or state.task.job_id.uuid != job.id:
                return
            await runtime.fence(session, job)
            started = state.start(state.task.job_id, self._clock.now())
            if started is not state:
                await states.save(started)
            task = started.task
        assert task is not None
        settings = task.snapshot.settings.format_settings
        if task.snapshot.engine_version != EXPORT_ENGINE_VERSION:
            raise ValueError("Unsupported feed export snapshot.")

        access = _CatalogAccess(
            runtime.tenant, task.requested_by.uuid, self._authorization
        )
        reader = _BatchReader(runtime, feed_id, access)
        try:
            context = await reader.prepare(task)
        except InvalidFeedValueError:
            output = TemporaryRefreshOutput(settings, ())
            try:
                await self._finish(
                    runtime,
                    job,
                    feed_id,
                    task,
                    ExportCountsVO(),
                    output,
                    failed_code="CATEGORY_CONFIGURATION_INVALID",
                )
            finally:
                output.close()
            return
        documents = tuple(
            resolver.field.export.document
            for resolver in context.category_fields
            if resolver.field.export.document is not None
        )
        output = TemporaryRefreshOutput(
            settings,
            tuple(field.export for field in context.exported_fields),
            shop=any(document.parent == "SHOP" for document in documents),
            has_document_sections=bool(documents),
            feed_name=context.feed.name,
            as_of=context.as_of,
        )
        try:
            try:
                counts = await ExecuteFeedRefreshHandler(reader).execute(
                    ExecuteFeedRefreshCommand(context), output
                )
            except ExportCatalogDenied:
                await self._finish(
                    runtime,
                    job,
                    feed_id,
                    task,
                    ExportCountsVO(),
                    output,
                    failed_code="SOURCE_ACCESS_DENIED",
                )
            else:
                await self._finish(runtime, job, feed_id, task, counts, output)
        finally:
            output.close()

    async def _finish(
        self,
        runtime: _Runtime,
        job: ScheduledJob,
        feed_id: FeedIdVO,
        task: ExportTaskVO,
        counts: ExportCountsVO,
        output: TemporaryRefreshOutput,
        *,
        failed_code: str | None = None,
    ) -> None:
        """Регистрирует готовый файл и фиксирует результат после проверки аренды."""
        file_id = None
        async with runtime.transaction() as session:
            files = build_files_handlers(session)
            if (
                failed_code is None
                and publication_rejection_reason(
                    task.snapshot.settings.validation_policy, counts
                )
                is None
            ):
                # Upload precedes the row locks. The registry entry rolls back if the lease was lost.
                source, size = output.upload_source()
                uploaded = await files.upload.execute(
                    UploadFileCommand(
                        runtime.tenant,
                        source,
                        size,
                        f"feed.{output.format.value}",
                        EXPORT_MEDIA_TYPES[output.format],
                    )
                )
                file_id = uploaded.file_id
            feed = await SqlAlchemyFeedRepository(session).get_for_update(feed_id)
            state = await SqlAlchemyFeedExportStateRepository(session).get_for_update(
                feed_id
            )
            if state.task is None or state.task.job_id.uuid != job.id:
                raise ScheduledJobDeferred("Feed export changed.")
            await runtime.fence(session, job)
            if file_id is not None:
                await files.lock_ready.execute(
                    LockReadyFileCommand(runtime.tenant, file_id)
                )
            await runtime.finish(session).finish(
                tenant_id=runtime.tenant,
                feed=feed,
                state=state,
                task=state.task,
                counts=counts,
                issues=output.issues() if failed_code is None else (),
                file_id=file_id,
                failed_code=failed_code,
            )


class ReconcileFeedExportJobHandler:
    """Закрывает состояние после исчерпания технических повторов."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], naming: TenantSchemaNaming
    ) -> None:
        """Принимает фабрику worker."""
        self._sessions, self._naming = sessions, naming

    async def handle(self, job: ScheduledJob) -> None:
        """Дожидается терминального состояния исходной задачи."""
        if job.tenant_id is None:
            raise ValueError("Feed export reconciliation requires tenant.")
        feed_id = FeedIdVO(UUID(job.payload["feed_id"]))
        job_id = UUID(job.payload["job_id"])
        runtime = _Runtime(self._sessions, job.tenant_id, UtcClock(), self._naming)
        async with runtime.transaction() as session:
            feed = await SqlAlchemyFeedRepository(session).get_for_update(feed_id)
            state = await SqlAlchemyFeedExportStateRepository(session).get_for_update(
                feed_id
            )
            if state.task is None or state.task.job_id.uuid != job_id:
                return
            terminal = await build_scheduled_job_repository(
                session
            ).terminal_or_missing(tenant_id=runtime.tenant, job_ids=[job_id])
            if job_id not in terminal:
                raise ScheduledJobDeferred("Feed export is still scheduled.")
            await runtime.fence(session, job)
            await runtime.finish(session).finish(
                tenant_id=runtime.tenant,
                feed=feed,
                state=state,
                task=state.task,
                counts=ExportCountsVO(),
                failed_code="REFRESH_FAILED",
            )


class RetireFeedExportFileJobHandler:
    """Удаляет заменённый файл через штатный lifecycle Files."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], naming: TenantSchemaNaming
    ) -> None:
        """Принимает фабрику worker."""
        self._sessions, self._naming = sessions, naming

    async def handle(self, job: ScheduledJob) -> None:
        """Переносит прежний файл в purge после окна для открытых потоков."""
        if job.tenant_id is None:
            raise ValueError("Feed file cleanup requires tenant.")
        runtime = _Runtime(self._sessions, job.tenant_id, UtcClock(), self._naming)
        file_id, actor = UUID(job.payload["file_id"]), UUID(job.payload["actor_id"])
        async with runtime.transaction() as session:
            await runtime.fence(session, job)
            files = build_files_handlers(session)
            try:
                try:
                    await files.trash_file.execute(
                        TrashFileCommand(runtime.tenant, file_id, actor)
                    )
                except FileStateConflictError:
                    # A replay can observe the file already queued for purge.
                    pass
                await files.request_purge.execute(
                    RequestFilePurgeCommand(runtime.tenant, file_id, actor)
                )
            except FileNotFoundError:
                return
