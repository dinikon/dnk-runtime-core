from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.infrastructure.channel.persistence.settings import (
    read_stock_sync_settings,
)
from src.modules.channels.infrastructure.platforms.rozetka.stock import (
    known_stock_target,
)
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.application.stock_sync.ports import (
    StockPublication,
    StockSyncRow,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.stock_sync import (
    StockSyncModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)


class SqlAlchemyStockRead:
    """Возвращает конкретные проекции собственных таблиц Channels."""

    def __init__(
        self,
        session: AsyncSession,
        jobs: ScheduledJobRepositoryProtocol,
        tenant_id: UUID,
    ) -> None:
        """Получает общую tenant-сессию и порт состояния Shared Jobs."""
        self.session, self.jobs, self.tenant_id = session, jobs, tenant_id

    async def publications(
        self, connection_id: UUID, ids: tuple[UUID, ...]
    ) -> tuple[StockPublication, ...]:
        """Загружает ограниченные затронутые семьи без полного raw_data."""
        if not ids:
            return ()
        platform_kind = await self.session.scalar(
            select(ChannelModel.platform_kind)
            .join(ConnectionModel, ConnectionModel.channel_id == ChannelModel.id)
            .where(ConnectionModel.id == connection_id)
        )
        table = ExternalPublicationModel.__table__
        parents = select(table.c.parent_id).where(table.c.id.in_(ids))
        rows = (
            await self.session.execute(
                select(
                    table.c.id,
                    table.c.resource_type,
                    table.c.external_id,
                    table.c.kind,
                    table.c.parent_id,
                    table.c.revision,
                    table.c.platform_data,
                    table.c.normalized_data,
                ).where(
                    table.c.connection_id == connection_id,
                    or_(
                        table.c.id.in_(ids),
                        table.c.parent_id.in_(ids),
                        table.c.id.in_(parents),
                        table.c.parent_id.in_(parents),
                    ),
                )
            )
        ).mappings()
        return tuple(
            StockPublication(
                PublicationLookup(
                    v["id"],
                    v["resource_type"],
                    v["external_id"],
                    v["kind"],
                    v["parent_id"],
                    v["revision"],
                    v["platform_data"],
                ),
                v["normalized_data"].get("stock_mode", "unknown"),
                v["normalized_data"].get("quantity"),
                v["normalized_data"].get("availability"),
                (
                    known_stock_target(v["platform_data"])
                    if platform_kind == "rozetka"
                    else None
                ),
            )
            for v in rows
        )

    async def states(
        self, connection_id: UUID, publication_ids: tuple[UUID, ...]
    ) -> tuple[StockSyncRow, ...]:
        """Читает результат с актуальностью политики и потерянным заданием."""
        rows = (
            await self.session.execute(
                select(
                    StockSyncModel,
                    ConnectionModel.config_revision,
                    ConnectionModel.settings,
                )
                .join(
                    ConnectionModel, ConnectionModel.id == StockSyncModel.connection_id
                )
                .join(ChannelModel, ChannelModel.id == ConnectionModel.channel_id)
                .where(
                    StockSyncModel.connection_id == connection_id,
                    StockSyncModel.publication_id.in_(publication_ids),
                )
            )
        ).all()
        inactive = await self.jobs.terminal_or_missing(
            tenant_id=self.tenant_id,
            job_ids=[
                s.operation_id
                for s, config_revision, settings in rows
                if s.status in {"queued", "running"}
            ],
        )
        result = []
        for state, config_revision, settings in rows:
            policy = read_stock_sync_settings(settings)
            stale = state.config_revision != config_revision or (
                state.direction == "write"
                and (
                    not policy.allow_export or state.policy_revision != policy.revision
                )
            )
            stale = stale and state.status in {"queued", "running"}
            lost = (
                not stale
                and state.status in {"queued", "running"}
                and state.operation_id in inactive
            )
            observed = state.observed or {}
            result.append(
                StockSyncRow(
                    state.publication_id,
                    state.operation_id,
                    state.direction,
                    "cancelled" if stale else "failed" if lost else state.status,
                    observed.get("quantity"),
                    observed.get("availability"),
                    state.observed_at,
                    state.desired_quantity,
                    "stock_job_interrupted" if lost else state.error_code,
                    state.updated_at,
                    lost,
                )
            )
        return tuple(result)
