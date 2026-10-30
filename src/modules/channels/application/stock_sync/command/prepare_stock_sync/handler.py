from src.modules.channels.application.stock_sync.command.prepare_stock_sync.command import (
    PrepareStockSyncCommand,
)
from src.modules.channels.application.stock_sync.command.prepare_stock_sync.dto import (
    PrepareStockSyncResultDTO,
)
from src.modules.channels.application.stock_sync.work import StockWorkSnapshot
from src.modules.channels.application.stock_sync.service import (
    StockPlanning,
    StockOperations,
)
from src.modules.channels.application.stock_sync.ports import (
    StockReadPort,
    StockJobsPort,
)
from src.modules.channels.domain.stock_sync.repository import (
    StockSyncRepositoryProtocol,
)
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class PrepareStockSyncHandler:
    """Проверяет актуальность и фиксирует running в коротком UoW."""

    def __init__(
        self,
        *,
        channels: ChannelRepositoryProtocol,
        states: StockSyncRepositoryProtocol,
        planning: StockPlanning,
        read: StockReadPort,
        jobs: StockJobsPort,
        clock: ClockPort,
        operations: StockOperations,
    ) -> None:
        """Получает абстрактные порты одного tenant."""
        self.operations = operations
        self.channels, self.states, self.planning, self.read, self.jobs, self.clock = (
            channels,
            states,
            planning,
            read,
            jobs,
            clock,
        )

    async def execute(
        self, command: PrepareStockSyncCommand
    ) -> PrepareStockSyncResultDTO:
        """Сеть запускается только после успешной фиксации этого сценария."""
        if not await self.jobs.owns(
            tenant_id=command.tenant_id,
            job_id=command.operation_id,
            lock_token=command.lock_token,
        ):
            return PrepareStockSyncResultDTO(None)
        channel = await self.channels.get(
            EntityIdVO(command.channel_id), for_update=True
        )
        states = await self.states.for_operation(EntityIdVO(command.operation_id))
        if channel is None or not states:
            return PrepareStockSyncResultDTO(None)
        now = self.clock.now()
        items = await self.planning.connection_items(channel.connection.id.uuid, now)
        plans = {v.publication.lookup.id: v for v in items}
        valid = []
        for state in states:
            if not state.accepts_access(
                connection_id=channel.connection.id,
                config_revision=channel.connection.config_revision,
                policy_revision=channel.connection.stock_sync.revision,
                verified=channel.connection.verification.status == "verified",
                export_allowed=channel.connection.stock_sync.allow_export,
            ):
                state.cancel(now=now)
                await self.states.save(state)
                continue
            plan = plans.get(state.publication_id.uuid)
            if (
                plan is None
                or plan.group.id != state.binding_group_id.uuid
                or plan.group.revision != state.binding_revision
            ):
                state.cancel(now=now)
                await self.states.save(state)
                continue
            valid.append((state, plan))
        if any(
            state.direction == "write"
            and state.status == "completed"
            and state.desired_state is not None
            and state.desired_state != plan.desired
            for state, plan in valid
        ):
            for state, plan in valid:
                state.cancel(now=now)
                await self.states.save(state)
            first = valid[0][1]
            await self.operations.request(
                tenant_id=command.tenant_id,
                channel_id=command.channel_id,
                group_id=first.group.id,
                direction="write",
                publication_ids=(),
                now=now,
            )
            return PrepareStockSyncResultDTO(None)
        valid.sort(
            key=lambda pair: (
                pair[1].publication.lookup.parent_id is not None,
                str(pair[0].publication_id.uuid),
            )
        )
        by_publication = {state.publication_id.uuid: state for state, plan in valid}
        for state, plan in valid:
            if state.status not in {"queued", "running"}:
                continue
            dependency = by_publication.get(plan.publication.lookup.parent_id)
            if (
                state.direction == "write"
                and plan.features.inheritance
                and dependency is not None
            ):
                if dependency.status in {"failed", "cancelled"}:
                    state.reject(
                        operation_id=state.operation_id,
                        error_code="stock_dependency_failed",
                        now=now,
                    )
                    await self.states.save(state)
                    continue
                if dependency.status != "completed":
                    continue
            if state.direction == "write":
                try:
                    self.planning.ensure_exportable(plan, items)
                except StockSyncError as exc:
                    state.reject(
                        operation_id=state.operation_id, error_code=exc.code, now=now
                    )
                    await self.states.save(state)
                    continue
            state.start(
                operation_id=state.operation_id,
                desired=plan.desired if state.direction == "write" else None,
                now=now,
            )
            await self.states.save(state)
            family = await self.read.publications(
                state.connection_id.uuid, (plan.publication.lookup.id,)
            )
            return PrepareStockSyncResultDTO(
                StockWorkSnapshot(
                    channel.platform_kind,
                    channel.connection.config,
                    channel.connection.encrypted_credentials,
                    state.direction,
                    state.revision,
                    plan,
                    family,
                )
            )
        return PrepareStockSyncResultDTO(None)
