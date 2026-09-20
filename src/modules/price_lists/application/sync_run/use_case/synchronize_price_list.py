import asyncio
from collections import Counter
from contextlib import aclosing
import logging
import time
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.price_lists.application.sync_run.ports import (
    ImportTransactionFactory,
    SourceFetcher,
    SourceParserPort,
    SourceCipher,
    CalendarPort,
    IdentifierPort,
    PriceListLock,
    ImportObserver,
)
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.application.sync_run.command.synchronize_price_list_command import (
    SynchronizePriceListCommand,
)
from src.modules.price_lists.domain.price_list.error import PriceListNotFoundError
from src.modules.price_lists.domain.sync_run.error import LostJobLease
from src.modules.price_lists.domain.sync_run.entity import SyncRun
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO

logger = logging.getLogger(__name__)


class SynchronizePriceListUseCase:
    """Скачивает, проверяет и атомарно публикует потоковый импорт."""

    def __init__(
        self,
        transactions: ImportTransactionFactory,
        fetcher: SourceFetcher,
        parser: SourceParserPort,
        cipher: SourceCipher,
        calendar: CalendarPort,
        identifiers: IdentifierPort,
        lock: PriceListLock,
        clock: ClockPort,
        options: ImportOptions,
        observer: ImportObserver,
    ):
        self.transactions = transactions
        self.fetcher = fetcher
        self.parser = parser
        self.cipher = cipher
        self.calendar = calendar
        self.identifiers = identifiers
        self.lock = lock
        self.clock = clock
        self.options = options
        self.observer = observer

    async def __call__(self, command: SynchronizePriceListCommand) -> None:
        """Сериализует один прайс, не ограничивая параллелизм других."""
        async with self.lock.hold(command.tenant_id, command.price_list_id) as acquired:
            if not acquired:
                raise ScheduledJobDeferred("Price list is already synchronizing")
            async with self.transactions() as tx:
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token
                )
                try:
                    price = await tx.prices.get(
                        command.tenant_id, command.price_list_id, for_update=True
                    )
                except PriceListNotFoundError:
                    return
                if (
                    price.status != "active"
                    or price.schedule_revision != command.revision
                ):
                    return
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token, fence=True
                )
                if command.trigger != "manual" and price.cron_expression:
                    next_at = self.calendar.next(
                        price.cron_expression,
                        price.timezone,
                        after=max(command.planned_at, self.clock.now()),
                    )
                    await tx.jobs.schedule_sync(
                        command.tenant_id,
                        price.id,
                        price.schedule_revision,
                        next_at,
                        "cron",
                    )
                    price.update(
                        {"next_sync_at": next_at}, price.updated_by, self.clock.now()
                    )
                    await tx.prices.save(command.tenant_id, price)
                run = await tx.runs.find_by_job(
                    command.tenant_id, price.id, command.job_id
                )
                if run is not None and run.published:
                    return
                if run is None:
                    run = SyncRun.create(
                        SyncRunIdVO.from_value(self.identifiers.new()),
                        price.id,
                        command.job_id,
                        command.trigger,
                        command.planned_at,
                        self.clock.now(),
                    )
                    await tx.runs.add(command.tenant_id, run)
            await self.clear_staging(command, run.id)
            run.reset(self.clock.now())
            async with self.transactions() as tx:
                await self.require_current(tx, command, fence=True)
                await tx.runs.save(command.tenant_id, run)
            await self.synchronize(command, price, run)

    async def clear_staging(self, command, run_id, *, keep_quarantine=False):
        """Удаляет staging короткими транзакциями без гигантского DELETE."""
        while True:
            async with self.transactions() as tx:
                await tx.jobs.require_lease(
                    command.tenant_id, command.job_id, command.lock_token
                )
                deleted = await tx.staging.delete_batch(
                    command.tenant_id, run_id, keep_quarantine=keep_quarantine
                )
            if not deleted:
                return

    async def synchronize(self, command, price, run):
        """Проводит фазы импорта с постоянным ограничением Python памяти."""
        committed = False
        started = time.monotonic()
        counters = Counter(
            dict(
                read=0,
                valid=0,
                rejected=0,
                created=0,
                changed=0,
                unchanged=0,
                missing=0,
                reappeared=0,
                ignored=0,
                quarantined=0,
            )
        )
        try:
            phase = time.monotonic()
            async with self.fetcher.open(
                self.cipher.decrypt(price.source_url_secret)
            ) as fetched:
                self.observer.downloaded(price.source_format, fetched.size)
                self.observer.phase(
                    "download", price.source_format, time.monotonic() - phase
                )
                run.source_checksum = fetched.checksum
                run.status = "parsing"
                phase = time.monotonic()
                async with aclosing(
                    self.parser.batches(
                        fetched.path,
                        price.source_format,
                        price.source_config,
                        price.mapping_config,
                    )
                ) as batches:
                    async for rows in batches:
                        counters["read"] += len(rows)
                        rejected = sum(bool(row.errors) for row in rows)
                        counters["rejected"] += rejected
                        counters["valid"] += len(rows) - rejected
                        run.counters = dict(counters)
                        async with self.transactions() as tx:
                            await self.require_current(tx, command, fence=True)
                            await tx.staging.append(command.tenant_id, run.id, rows)
                            await tx.runs.save(command.tenant_id, run)
                        self.observer.batch(
                            "parse_stage", price.source_format, len(rows)
                        )
                self.observer.phase(
                    "parse_stage", price.source_format, time.monotonic() - phase
                )
            run.validate(self.options.max_error_ratio)
            run.status = "applying"
            async with self.transactions() as tx:
                await self.require_current(tx, command, fence=True)
                await tx.runs.save(command.tenant_id, run)
            phase = time.monotonic()
            async with self.transactions() as tx:
                await self.require_current(tx, command)
                after = 0
                while rows := await tx.staging.read_batch(
                    command.tenant_id, run.id, after, self.options.batch_size
                ):
                    after = rows[-1].row_number
                    values = [row.offer_values() for row in rows if not row.errors]
                    ids = [
                        (
                            OfferIdVO.from_value(self.identifiers.new()),
                            OfferStateIdVO.from_value(self.identifiers.new()),
                        )
                        for _ in values
                    ]
                    changes, quarantined = await tx.offer_service.apply_batch(
                        command.tenant_id, price, run.id, values, ids
                    )
                    counters.update(changes)
                    self.observer.batch("publish", price.source_format, len(rows))
                    await tx.staging.quarantine(command.tenant_id, run.id, quarantined)
                if not counters["rejected"]:
                    after_id = None
                    while True:
                        batch = await tx.offers.missing_batch(
                            command.tenant_id,
                            price.id,
                            run.id,
                            after_id,
                            self.options.batch_size,
                        )
                        if batch.after_id is None:
                            break
                        after_id = batch.after_id
                        offers = batch.items
                        if not offers:
                            continue
                        changes = await tx.offer_service.apply_missing_batch(
                            command.tenant_id,
                            price,
                            run.id,
                            offers,
                            [
                                OfferStateIdVO.from_value(self.identifiers.new())
                                for _ in offers
                            ],
                        )
                        counters.update(changes)
                        self.observer.batch("missing", price.source_format, len(offers))
                current = await self.require_current(tx, command, fence=True)
                run.counters = dict(counters)
                run.finish(self.clock.now())
                await tx.runs.save(command.tenant_id, run)
                current.update(
                    dict(last_sync_run_id=run.id, last_success_at=run.finished_at),
                    current.updated_by,
                    run.finished_at,
                )
                await tx.prices.save(command.tenant_id, current)
            committed = True
            self.observer.phase(
                "publish", price.source_format, time.monotonic() - phase
            )
        except BaseException as exc:
            if not committed:
                try:
                    async with asyncio.timeout(5):
                        async with self.transactions() as tx:
                            current = await self.require_current(
                                tx, command, fence=True
                            )
                            run.counters = dict(counters)
                            run.finish(
                                self.clock.now(),
                                error=f"{type(exc).__name__}: synchronization failed",
                            )
                            await tx.runs.save(command.tenant_id, run)
                            current.update(
                                dict(
                                    last_sync_run_id=run.id,
                                    last_error_at=run.finished_at,
                                ),
                                current.updated_by,
                                run.finished_at,
                            )
                            await tx.prices.save(command.tenant_id, current)
                except Exception:
                    logger.warning(
                        "Could not finalize run: run_id=%s error_type=%s",
                        run.id,
                        type(exc).__name__,
                    )
            self.observer.completed(
                price.source_format,
                command.trigger,
                "failed",
                dict(counters),
                time.monotonic() - started,
            )
            raise
        self.observer.completed(
            price.source_format,
            command.trigger,
            run.status,
            dict(counters),
            time.monotonic() - started,
        )
        # Publication is already durable; cleanup errors must not fail a successful import.
        try:
            await self.clear_staging(command, run.id, keep_quarantine=True)
        except Exception:
            logger.info("Staging cleanup deferred: run_id=%s", run.id)

    async def require_current(self, tx, command, *, fence=False):
        """Порядок блокировок совпадает с lifecycle: price, затем job."""
        current = await tx.prices.get(
            command.tenant_id, command.price_list_id, for_update=fence
        )
        if current.status != "active" or current.schedule_revision != command.revision:
            raise LostJobLease("Price-list schedule is no longer current.")
        await tx.jobs.require_lease(
            command.tenant_id, command.job_id, command.lock_token, fence=fence
        )
        return current


__all__ = ["SynchronizePriceListUseCase"]
