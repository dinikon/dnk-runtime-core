from src.modules.channels.application.batch_export.artifacts import export_artifact_id
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel as H,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as C,
)
from src.modules.channels.infrastructure.persistence.models.export_schedule import (
    ExportScheduleModel as S,
)
from src.modules.channels.application.batch_export.port.queries import (
    BatchExportChannelScopeDTO,
)
from src.modules.channels.application.batch_export.query.get_batch_export_overview.dto import (
    ExportScheduleDTO,
)
from uuid import UUID, uuid5
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.batch_export import (
    BatchExportRunModel as R,
    BatchExportItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel as B,
)
from src.modules.channels.application.batch_export.contracts import (
    BatchExportSummaryDTO,
    BatchExportItemDTO,
)
from src.modules.channels.application.batch_export.query.get_batch_export.dto import (
    BatchExportDetailDTO,
)
from src.modules.channels.application.batch_export.port.queries import ExportFeedDTO
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyBatchExportQueries:
    """Читает собственные проекции без приватных метаданных и восстановления корня."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию без commit и доступа к чужим ORM."""
        self.session = session

    async def scope(self, run_id: UUID) -> UUID:
        """Разрешает идентификатор только в текущей tenant-схеме."""
        identifier = await self.session.scalar(
            select(R.channel_id).where(R.id == run_id)
        )
        if identifier is None:
            raise ChannelsNotFoundError("batch_export_not_found")
        return identifier

    async def summary(self, run_id: UUID) -> BatchExportSummaryDTO:
        """Читает один header с агрегированными счётчиками."""
        row = (
            await self.session.execute(
                select(
                    R.id,
                    R.channel_id,
                    R.trigger,
                    R.status,
                    R.created_at,
                    R.updated_at,
                    R.error_code,
                    R.delivery_mode,
                ).where(R.id == run_id)
            )
        ).one_or_none()
        if row is None:
            raise ChannelsNotFoundError("batch_export_not_found")
        counts = dict(
            (
                await self.session.execute(
                    select(I.status, func.count())
                    .where(I.run_id == run_id)
                    .group_by(I.status)
                )
            ).all()
        )
        return BatchExportSummaryDTO(*row[:-1], counts, delivery_mode=row.delivery_mode)

    async def detail(
        self, run_id: UUID, offset: int, limit: int
    ) -> BatchExportDetailDTO:
        """Не читает baseline, provider context и адрес подписанного файла."""
        summary = await self.summary(run_id)
        rows = (
            await self.session.execute(
                select(
                    I.publication_id,
                    I.catalog_item_id,
                    I.external_id,
                    I.status,
                    I.issues,
                    I.desired,
                )
                .where(I.run_id == run_id)
                .order_by(I.publication_id)
                .offset(offset)
                .limit(limit)
            )
        ).mappings()
        items = tuple(
            BatchExportItemDTO(
                row["publication_id"],
                row["catalog_item_id"],
                row["external_id"],
                row["status"],
                tuple(row["issues"]),
                (
                    {
                        t["locale"]: t["title"]
                        for t in row["desired"]["translations"]
                        if t["title"]
                    }
                    if row["desired"]
                    else {}
                ),
            )
            for row in rows
        )
        return BatchExportDetailDTO(summary, items, sum(summary.counts.values()))

    async def recent(self, channel_id: UUID) -> tuple[BatchExportSummaryDTO, ...]:
        """Возвращает ограниченную историю канала для всех уполномоченных операторов."""
        ids = (
            await self.session.scalars(
                select(R.id)
                .where(R.channel_id == channel_id)
                .order_by(R.created_at.desc(), R.id.desc())
                .limit(20)
            )
        ).all()
        return tuple([await self.summary(identifier) for identifier in ids])

    async def eligibility(self, connection_id: UUID) -> tuple[int, int]:
        """Считает активные связи и явные разрешения без присоединения Catalog."""
        row = (
            await self.session.execute(
                select(func.count(), func.count().filter(P.export_enabled.is_(True)))
                .select_from(P)
                .join(B, B.representation_id == P.id)
                .where(P.connection_id == connection_id, B.released_at.is_(None))
            )
        ).one()
        return row[0], row[1]

    async def feed(self, run_id: UUID) -> ExportFeedDTO:
        """Публикует только завершённый файл зафиксированной операции."""
        row = (
            await self.session.execute(
                select(R.id, R.expires_at, R.artifact_hash, R.artifact_size).where(
                    R.id == run_id,
                    R.artifact_hash.is_not(None),
                    R.artifact_size.is_not(None),
                    R.status.in_(
                        (
                            "prepared",
                            "submitting",
                            "processing",
                            "verifying",
                            "unknown",
                            "succeeded",
                            "partial",
                        )
                    ),
                )
            )
        ).one_or_none()
        if row is None:
            raise ChannelsNotFoundError("export_feed_not_found")
        return ExportFeedDTO(export_artifact_id(row[0]), row[1], row[2], row[3])

    async def current_job(self, run_id: UUID) -> UUID | None:
        """Вычисляет ID только активного шага, не принимая status очереди за Domain state."""
        row = (
            await self.session.execute(
                select(R.sequence, R.status).where(R.id == run_id)
            )
        ).one_or_none()
        if row is None or row.status in (
            "unknown",
            "succeeded",
            "partial",
            "failed",
            "empty",
            "prepared",
        ):
            return None
        return uuid5(run_id, "batch:" + str(row.sequence))

    async def channel_scope(self, channel_id: UUID) -> BatchExportChannelScopeDTO:
        """Проецирует только параметры возможностей и разрешения исходящих операций."""
        row = (
            await self.session.execute(
                select(C.id, H.platform_kind, H.is_enabled)
                .join(H, H.id == C.channel_id)
                .where(H.id == channel_id)
            )
        ).one_or_none()
        if row is None:
            raise ChannelsNotFoundError("connection_not_configured")
        return BatchExportChannelScopeDTO(*row)

    async def schedule(self, channel_id: UUID) -> ExportScheduleDTO:
        """Не восстанавливает корень policy для обычного чтения формы."""
        row = (
            await self.session.execute(
                select(
                    S.enabled, S.hour, S.minute, S.timezone, S.revision, S.next_at
                ).where(S.channel_id == channel_id)
            )
        ).one_or_none()
        return (
            ExportScheduleDTO(*row)
            if row
            else ExportScheduleDTO(False, 3, 0, "Europe/Kyiv", 1, None)
        )
