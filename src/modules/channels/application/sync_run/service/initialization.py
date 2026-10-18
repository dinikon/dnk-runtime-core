from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID, uuid5
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.sync_run.aggregate import SyncRun
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class InitializationService:
    """Координирует старт, checkpoint и задания без вызовов других handlers."""

    def __init__(
        self,
        runs: SyncRunRepositoryProtocol,
        jobs: ChannelsJobsProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей транзакции и источники времени/ID."""
        self.runs, self.jobs, self.clock, self.identifiers = (
            runs,
            jobs,
            clock,
            identifiers,
        )

    async def cancel_active(self, channel: Channel) -> None:
        """Останавливает текущий run перед сменой generation или паузой."""
        if channel.connection:
            run = await self.runs.latest(channel.connection.id)
            if run and run.status in ("queued", "running"):
                run.cancel(self.clock.now())
                await self.runs.save(run)

    async def start(
        self,
        tenant_id: UUID,
        channel: Channel,
        actor_id: UUID,
        request_key: UUID,
        *,
        automatic: bool = False,
    ) -> SyncRun:
        """Идемпотентно начинает/продолжает чтение; automatic не повторяет завершённое."""
        connection = channel.require_connection()
        previous = await self.runs.by_request(
            connection.id, EntityIdVO.from_value(request_key)
        )
        if previous:
            return previous
        channel.ensure_network()
        latest = await self.runs.latest(connection.id)
        if latest and latest.status in ("queued", "running"):
            if latest.job_id and await self.jobs.is_recoverable(
                tenant_id, latest.job_id.uuid
            ):
                latest.register_request(EntityIdVO.from_value(request_key))
                await self.runs.save(latest)
                return latest
            latest.fail("background_job_unavailable", self.clock.now())
            await self.runs.save(latest)
        if (
            automatic
            and latest
            and (latest.status in ("succeeded", "partial"))
            and (latest.reason_code in (None, "scope_limited", "invalid_rows"))
        ):
            latest.register_request(EntityIdVO.from_value(request_key))
            await self.runs.save(latest)
            return latest
        if (
            latest
            and latest.status in ("failed", "partial", "cancelled")
            and (not latest.read_complete)
            and (latest.generation == connection.generation)
        ):
            latest.retry(
                EntityIdVO.from_value(request_key),
                connection.generation,
                connection.scope_limitations,
                self.clock.now(),
            )
            await self.runs.save(latest)
            run = latest
        else:
            run = SyncRun.create(
                EntityIdVO.from_value(self.identifiers.new()),
                EntityIdVO.from_value(channel.id),
                EntityIdVO.from_value(connection.id),
                connection.generation,
                EntityIdVO.from_value(actor_id),
                EntityIdVO.from_value(request_key),
                connection.scope_limitations,
                self.clock.now(),
            )
            await self.runs.add(run)
        await self.schedule(tenant_id, run)
        return run

    async def schedule(
        self, tenant_id: UUID, run: SyncRun, delay_seconds: int = 0
    ) -> None:
        """Сохраняет job ID и очередь в общей транзакции текущего шага."""
        from datetime import timedelta

        job_id = uuid5(run.id.uuid, f"page:{run.sequence}")
        run.schedule(EntityIdVO.from_value(job_id))
        await self.runs.save(run)
        await self.jobs.page(
            tenant_id,
            run.id.uuid,
            job_id,
            run.sequence,
            self.clock.now() + timedelta(seconds=delay_seconds),
        )
