from src.modules.channels.application.stock_sync.command.prepare_stock_sync.command import (
    PrepareStockSyncCommand,
)
from src.modules.channels.application.stock_sync.command.prepare_stock_sync.dto import (
    PrepareStockSyncResultDTO,
)
from src.modules.channels.application.stock_sync.work import StockWorkSnapshot
from src.modules.channels.application.stock_sync.service import StockPlanning
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
    ) -> None:
        """Получает абстрактные порты одного tenant."""
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
        state = await self.states.get(EntityIdVO(command.publication_id))
        if (
            channel is None
            or state is None
            or state.operation_id.uuid != command.operation_id
            or state.status not in {"queued", "running"}
        ):
            return PrepareStockSyncResultDTO(None)
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
            return PrepareStockSyncResultDTO(None)
        items = await self.planning.connection_items(state.connection_id.uuid, now)
        plan = next(
            (
                v
                for v in items
                if v.owner.lookup.id == state.publication_id.uuid
                and v.group.id == state.binding_group_id.uuid
                and v.group.revision == state.binding_revision
            ),
            None,
        )
        if plan is None:
            state.cancel(now=now)
            await self.states.save(state)
            return PrepareStockSyncResultDTO(None)
        error = None
        if state.direction == "write":
            try:
                self.planning.ensure_exportable(plan, items)
            except StockSyncError as exc:
                error = exc.code
        if error:
            state.reject(
                operation_id=EntityIdVO(command.operation_id), error_code=error, now=now
            )
            await self.states.save(state)
            return PrepareStockSyncResultDTO(None)
        state.start(
            operation_id=EntityIdVO(command.operation_id),
            quantity=plan.facts.quantity if state.direction == "write" else None,
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
