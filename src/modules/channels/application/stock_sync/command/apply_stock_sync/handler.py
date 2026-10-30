from src.modules.channels.application.stock_sync.command.apply_stock_sync.command import (
    ApplyStockSyncCommand,
)
from src.modules.channels.application.stock_sync.ports import (
    StockJobsPort,
    StockPublicationWriter,
)
from src.modules.channels.application.stock_sync.service import (
    StockOperations,
    StockPlanning,
)
from src.modules.channels.domain.stock_sync.repository import (
    StockSyncRepositoryProtocol,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class ApplyStockSyncHandler:
    """Применяет наблюдение только при действующем lease и поколении состояния."""

    def __init__(
        self,
        *,
        channels: ChannelRepositoryProtocol,
        states: StockSyncRepositoryProtocol,
        jobs: StockJobsPort,
        publications: StockPublicationWriter,
        operations: StockOperations,
        planning: StockPlanning,
        clock: ClockPort,
    ) -> None:
        """Не получает SQL session и не вызывает сеть."""
        (
            self.channels,
            self.states,
            self.jobs,
            self.publications,
            self.operations,
            self.planning,
            self.clock,
        ) = (channels, states, jobs, publications, operations, planning, clock)

    async def execute(self, command: ApplyStockSyncCommand) -> None:
        """После изменения Catalog во время API планирует актуальное исправление."""
        job, snapshot = command.job, command.snapshot
        channel = await self.channels.get(EntityIdVO(job.channel_id), for_update=True)
        state = await self.states.get(EntityIdVO(job.publication_id))
        if (
            channel is None
            or state is None
            or state.operation_id.uuid != job.operation_id
            or state.revision != snapshot.state_revision
        ):
            return
        if not await self.jobs.owns(
            tenant_id=job.tenant_id,
            job_id=job.operation_id,
            lock_token=job.lock_token,
            for_update=True,
        ):
            return
        now = self.clock.now()
        if not state.accepts_access(
            connection_id=channel.connection.id,
            config_revision=channel.connection.config_revision,
            policy_revision=channel.connection.stock_sync.revision,
            verified=channel.connection.verification.status == "verified",
            export_allowed=channel.connection.stock_sync.allow_export,
        ):
            state.cancel(now=now)
            await self.states.save(state)
            return
        items = await self.planning.connection_items(state.connection_id.uuid, now)
        current = next(
            (
                v
                for v in items
                if v.group.id == state.binding_group_id.uuid
                and v.group.revision == state.binding_revision
                and v.owner.lookup.id == state.publication_id.uuid
            ),
            None,
        )
        if current is None:
            state.cancel(now=now)
            await self.states.save(state)
            return
        if command.result is not None and command.owner_id is not None:
            await self.publications.apply(
                connection_id=state.connection_id.uuid,
                publication_id=snapshot.plan.publication.lookup.id,
                owner_id=command.owner_id,
                stock=command.result.stock,
                platform_data=command.result.platform_data,
                config_revision=state.config_revision,
                now=now,
            )
        state.complete(
            operation_id=EntityIdVO(job.operation_id),
            snapshot=command.result.stock if command.result else None,
            error_code=command.error_code,
            now=now,
        )
        await self.states.save(state)
        if (
            state.direction == "write"
            and (current.facts.quantity, current.facts.backorders)
            != (snapshot.plan.facts.quantity, snapshot.plan.facts.backorders)
            and current.facts.quantity is not None
        ):
            await self.operations.request(
                tenant_id=job.tenant_id,
                channel_id=job.channel_id,
                group_id=current.group.id,
                direction="write",
                publication_ids=(current.publication.lookup.id,),
                now=now,
            )
