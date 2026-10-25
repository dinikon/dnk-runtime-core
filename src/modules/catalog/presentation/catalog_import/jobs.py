import asyncio
import hashlib
import logging
import time
from collections.abc import Iterator
from collections.abc import Callable
from dataclasses import asdict
from itertools import islice
from functools import partial
from typing import TypeVar
from uuid import UUID, uuid5
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from prometheus_client import Counter, Histogram
from src.config import dnk_config
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport, TERMINAL
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogDependencyUnavailableError,
    InvalidCatalogValueError,
)
from src.modules.catalog.application.catalog_import.contracts import (
    SourceRecord,
    SourceField,
)
from src.modules.catalog.application.catalog_import.values import mapped_values, scalar
from src.modules.catalog.application.catalog_import.command.prepare_catalog_import.handler import (
    PrepareCatalogImportHandler,
)
from src.modules.catalog.application.catalog_import.command.prepare_catalog_import.command import (
    PrepareCatalogImportCommand,
)
from src.modules.catalog.application.catalog_import.command.process_catalog_import_batch.handler import (
    ProcessCatalogImportBatchHandler,
)
from src.modules.catalog.application.catalog_import.command.process_catalog_import_batch.command import (
    ProcessCatalogImportBatchCommand,
)
from src.modules.catalog.application.catalog_import.command.process_catalog_import_row.command import (
    ProcessCatalogImportRowCommand,
)
from src.modules.catalog.application.catalog_import.analysis_service import (
    build_import_analysis,
)
from src.modules.catalog.application.catalog_import.gallery_service import (
    ImportGalleryService,
)
from src.modules.catalog.infrastructure.catalog_import.media import PreparedImportMedia
from src.modules.catalog.application.catalog_import.progress_service import (
    ImportProgressService,
)
from src.modules.catalog.infrastructure.catalog_import.parser import CatalogImportParser
from src.modules.catalog.infrastructure.catalog_import.download import (
    download_public_file,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
    SqlAlchemyImportRows,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_import import (
    CatalogImportModel,
)
from src.modules.catalog.presentation.catalog_import.runtime import CatalogImportRuntime
from src.modules.catalog.presentation.catalog_import.assembly import (
    build_import_queue,
    build_process_import_row,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable

logger = logging.getLogger(__name__)
import_rows_total = Counter(
    "catalog_import_rows_total", "Committed import row outcomes", ["outcome"]
)
import_jobs_total = Counter(
    "catalog_import_jobs_total", "Import worker outcomes", ["phase", "outcome"]
)
import_job_seconds = Histogram(
    "catalog_import_job_seconds", "Import job duration", ["phase"]
)

ParserResult = TypeVar("ParserResult")


async def run_parser(action: Callable[[], ParserResult]) -> ParserResult:
    """Дожидается локального чтения до закрытия spool также при отмене worker."""
    task = asyncio.create_task(asyncio.to_thread(action))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            pass
        raise


def take_rows(iterator: Iterator[SourceRecord], count: int) -> tuple[SourceRecord, ...]:
    """Читает ограниченную порцию вне event loop."""
    rows: list[SourceRecord] = []
    size = 0
    for row in islice(iterator, count):
        rows.append(row)
        size += sum(
            len(value.encode("utf-8"))
            for entries in row.values.values()
            for value in entries
        )
        if size >= 1024 * 1024:
            break
    return tuple(rows)


class CatalogImportJobHandler:
    """Внешняя сборка фонового процесса с короткими tenant UoW и fencing."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Не удерживает HTTP-контекст или request-scoped сессию."""
        self.sessions = sessions
        self.semaphore = asyncio.Semaphore(
            dnk_config.CATALOG_IMPORT.download_concurrency
        )

    async def fence(self, session: AsyncSession, job: ScheduledJob) -> None:
        """Запрещает commit устаревшему владельцу lease."""
        if not await build_scheduled_job_repository(session).owns_current_lease(
            job_id=job.id,
            tenant_id=job.tenant_id,
            lock_token=job.lock_token,
            for_update=True,
        ):
            raise ScheduledJobDeferred("Import lease is no longer current.")

    async def current(
        self, session: AsyncSession, job: ScheduledJob
    ) -> CatalogImport | None:
        """Блокирует запуск и отсекает старую версию или завершённое задание."""
        try:
            entity = await SqlAlchemyCatalogImportRepository(session).get(
                EntityIdVO(UUID(job.payload["import_id"])), lock=True
            )
        except CatalogNotFoundError:
            return None
        if (
            entity.version != job.payload["version"]
            or entity.generation != job.payload.get("generation", 0)
            or entity.status in TERMINAL
            or entity.job_id != EntityIdVO(job.id)
        ):
            return None
        return entity

    async def handle(self, job: ScheduledJob) -> None:
        """Выполняет подготовку либо пачку, сохраняя уже завершённые позиции."""
        if (
            job.tenant_id is None
            or not job.lock_token
            or job.job_type not in {"catalog.import.prepare", "catalog.import.run"}
        ):
            raise ValueError("Invalid catalog import envelope.")
        runtime = CatalogImportRuntime(self.sessions, job.tenant_id)
        phase = job.job_type.rsplit(".", 1)[-1]
        started = time.monotonic()
        try:
            if phase == "prepare":
                await self.prepare(runtime, job)
            else:
                await self.process(runtime, job)
            import_jobs_total.labels(phase, "committed").inc()
        except TenantUnavailable as error:
            raise ScheduledJobDeferred("Tenant admission unavailable.") from error
        except (asyncio.CancelledError, ScheduledJobDeferred):
            raise
        except Exception as error:
            import_jobs_total.labels(
                phase,
                (
                    "rejected"
                    if isinstance(error, InvalidCatalogValueError)
                    else (
                        "retry"
                        if job.attempts < dnk_config.SCHEDULED_JOBS.max_attempts
                        else "exhausted"
                    )
                ),
            ).inc()
            if (
                isinstance(error, InvalidCatalogValueError)
                or job.attempts >= dnk_config.SCHEDULED_JOBS.max_attempts
            ):
                async with runtime.transaction() as uow:
                    entity = await self.current(uow.session, job)
                    if entity is not None:
                        await ImportProgressService(
                            SqlAlchemyCatalogImportRepository(uow.session),
                            SqlAlchemyImportRows(uow.session),
                            UtcClock(),
                        ).fail(
                            entity.id.uuid,
                            (
                                str(error)
                                if isinstance(error, InvalidCatalogValueError)
                                else "Не удалось завершить импорт после повторных попыток."
                            ),
                        )
                        await self.fence(uow.session, job)
                if isinstance(error, InvalidCatalogValueError):
                    return
            raise
        finally:
            import_job_seconds.labels(phase).observe(time.monotonic() - started)

    async def prepare(self, runtime: CatalogImportRuntime, job: ScheduledJob) -> None:
        """Сохраняет один снимок и по частям строит staging с предпросмотром."""
        settings = dnk_config.CATALOG_IMPORT
        async with runtime.transaction() as uow:
            entity = await self.current(uow.session, job)
            if entity is None or entity.status != "preparing":
                return
        if entity.source_file_id is None:
            if entity.source_url is None:
                raise InvalidCatalogValueError("Источник импорта отсутствует.")
            downloaded = await download_public_file(
                entity.source_url,
                settings.source_max_bytes,
                settings.download_timeout_seconds,
            )
            digest = hashlib.sha256()
            while chunk := downloaded.source.read(65536):
                digest.update(chunk)
            downloaded.source.seek(0)
            source_id = uuid5(entity.id.uuid, "source:" + digest.hexdigest())
            try:
                await runtime.put(
                    source_id,
                    downloaded.source,
                    downloaded.size,
                    "catalog-import-source",
                    "application/octet-stream",
                )
            finally:
                downloaded.source.close()
            async with runtime.transaction() as uow:
                current = await self.current(uow.session, job)
                if current is None or current.status != "preparing":
                    return
                await ImportProgressService(
                    SqlAlchemyCatalogImportRepository(uow.session),
                    SqlAlchemyImportRows(uow.session),
                    UtcClock(),
                ).attach_source(current.id.uuid, source_id)
                current = await SqlAlchemyCatalogImportRepository(uow.session).get(
                    current.id
                )
                await self.fence(uow.session, job)
            entity = current
        source = await runtime.open(
            entity.source_file_id.uuid, settings.source_max_bytes
        )
        try:
            parser = CatalogImportParser(settings.max_records)
            description = await run_parser(
                partial(parser.inspect, source, entity.configuration)
            )
            async with runtime.transaction() as uow:
                if await self.current(uow.session, job) is None:
                    return
                await SqlAlchemyImportRows(uow.session).reset(entity.id.uuid)
                await uow.session.execute(
                    update(CatalogImportModel)
                    .where(CatalogImportModel.id == entity.id.uuid)
                    .values(analysis=asdict(description))
                )
                await self.fence(uow.session, job)
            total = 0
            samples: list[SourceRecord] = []
            fields = {f.id: f for f in description.fields}
            iterator = parser.records(source, description)
            try:
                while batch := await run_parser(partial(take_rows, iterator, 100)):
                    total += len(batch)
                    for row in batch:
                        for key in row.values:
                            fields.setdefault(key, SourceField(key, key))
                        if len(fields) > 2000:
                            raise InvalidCatalogValueError(
                                "Источник содержит слишком много различных полей."
                            )
                        if len(samples) < 20:
                            samples.append(
                                SourceRecord(
                                    row.number,
                                    {
                                        k: [v[:1000] for v in values[:100]]
                                        for k, values in row.values.items()
                                    },
                                )
                            )
                    async with runtime.transaction() as uow:
                        if await self.current(uow.session, job) is None:
                            return
                        await SqlAlchemyImportRows(uow.session).stage(
                            entity.id.uuid, batch
                        )
                        await self.fence(uow.session, job)
            finally:
                iterator.close()
            configuration, analysis = build_import_analysis(
                description,
                tuple(fields.values()),
                tuple(samples),
                entity.configuration,
            )
            async with runtime.transaction() as uow:
                current = await self.current(uow.session, job)
                if current is None:
                    return
                await PrepareCatalogImportHandler(
                    SqlAlchemyCatalogImportRepository(uow.session),
                    UtcClock(),
                    SqlAlchemyImportRows(uow.session),
                ).execute(
                    PrepareCatalogImportCommand(
                        current.id.uuid, current.version, total, configuration, analysis
                    )
                )
                await self.fence(uow.session, job)
        finally:
            source.close()

    async def process(self, runtime: CatalogImportRuntime, job: ScheduledJob) -> None:
        """Выполняет ограниченную пачку с атомарным commit каждой позиции."""
        started = time.monotonic()
        for _ in range(dnk_config.CATALOG_IMPORT.batch_size):
            async with runtime.transaction() as uow:
                entity = await self.current(uow.session, job)
                if entity is None:
                    return
                if entity.status == "cancelling":
                    await ImportProgressService(
                        SqlAlchemyCatalogImportRepository(uow.session),
                        SqlAlchemyImportRows(uow.session),
                        UtcClock(),
                    ).stop(entity.id.uuid)
                    await self.fence(uow.session, job)
                    return
                row = await SqlAlchemyImportRows(uow.session).next_row(entity.id.uuid)
                if row is None:
                    return
            sku: str | None = None
            warnings: tuple[str, ...] = ()
            try:
                values = mapped_values(entity.configuration, row.values)
                sku = scalar(values, "sku") or None
                galleries, warnings = await ImportGalleryService(
                    PreparedImportMedia(runtime, self.semaphore),
                    dnk_config.CATALOG_IMPORT.max_images,
                ).prepare(entity.id.uuid, entity.configuration, row)
                async with runtime.transaction() as uow:
                    current = await self.current(uow.session, job)
                    if current is None:
                        return
                    if current.status == "cancelling":
                        await ImportProgressService(
                            SqlAlchemyCatalogImportRepository(uow.session),
                            SqlAlchemyImportRows(uow.session),
                            UtcClock(),
                        ).stop(current.id.uuid)
                        await self.fence(uow.session, job)
                        return
                    result = await build_process_import_row(
                        uow.session, job.tenant_id
                    ).execute(
                        ProcessCatalogImportRowCommand(
                            entity.id.uuid, row, galleries, warnings
                        )
                    )
                    await self.fence(uow.session, job)
                if result.applied:
                    import_rows_total.labels(result.result.outcome).inc()
            except CatalogDependencyUnavailableError:
                raise
            except CatalogError as error:
                async with runtime.transaction() as uow:
                    current = await self.current(uow.session, job)
                    if current is None:
                        return
                    if current.status == "cancelling":
                        await ImportProgressService(
                            SqlAlchemyCatalogImportRepository(uow.session),
                            SqlAlchemyImportRows(uow.session),
                            UtcClock(),
                        ).stop(current.id.uuid)
                        await self.fence(uow.session, job)
                        return
                    applied = await ImportProgressService(
                        SqlAlchemyCatalogImportRepository(uow.session),
                        SqlAlchemyImportRows(uow.session),
                        UtcClock(),
                    ).record_error(
                        entity.id.uuid,
                        row.number,
                        sku,
                        (", ".join(error.fields) + ": " if error.fields else "")
                        + str(error),
                        warnings,
                    )
                    await self.fence(uow.session, job)
                if applied:
                    import_rows_total.labels("errors").inc()
            if time.monotonic() - started >= dnk_config.CATALOG_IMPORT.batch_seconds:
                break
        async with runtime.transaction() as uow:
            current = await self.current(uow.session, job)
            if current is not None:
                await ProcessCatalogImportBatchHandler(
                    SqlAlchemyCatalogImportRepository(uow.session),
                    build_import_queue(uow.session, job.tenant_id),
                    UtcClock(),
                ).execute(
                    ProcessCatalogImportBatchCommand(current.id.uuid, current.version)
                )
                await self.fence(uow.session, job)
