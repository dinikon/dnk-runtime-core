from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.funnel.domain.aggregate import Funnel
from src.modules.funnel.infrastructure.persistence.models.funnel import FunnelModel
from src.modules.funnel.infrastructure.persistence.models.stage import FunnelStageModel
from src.modules.funnel.infrastructure.persistence.mapper import FunnelMapper


class SqlAlchemyFunnelRepository:
    """Записывает процесс и стадии на общей сессии UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию tenant."""
        self._session = session

    async def get(
        self, funnel_id: EntityIdVO, *, for_update: bool = False
    ) -> Funnel | None:
        """Блокирует определение для записи либо согласованного domain-решения."""
        row = (
            (
                await self._session.execute(
                    select(FunnelModel.__table__)
                    .where(FunnelModel.id == funnel_id.uuid)
                    .with_for_update(read=not for_update)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        stages = (
            (
                await self._session.execute(
                    select(FunnelStageModel.__table__)
                    .where(FunnelStageModel.funnel_id == funnel_id.uuid)
                    .order_by(FunnelStageModel.position)
                )
            )
            .mappings()
            .all()
        )
        return FunnelMapper.to_domain(row, list(stages))

    async def get_default(self, model_key: str) -> Funnel | None:
        """Читает существующий default без скрытой записи."""
        record_id = (
            await self._session.execute(
                select(FunnelModel.id).where(
                    FunnelModel.model_key == model_key, FunnelModel.is_default.is_(True)
                )
            )
        ).scalar_one_or_none()
        return await self.get(EntityIdVO(record_id)) if record_id else None

    async def add(self, entity: Funnel) -> None:
        """Добавляет полный процесс без commit."""
        await self._session.execute(
            insert(FunnelModel).values(**FunnelMapper.to_values(entity))
        )
        await self._stages(entity, set())

    async def _stages(self, entity: Funnel, existing: set[UUID]) -> None:
        """Сохраняет ID существующих стадий; FK карточек остаются неизменны."""
        for position, stage in enumerate(entity.stages):
            values = dict(
                name=stage.name,
                color=stage.color.value,
                kind=stage.kind.value,
                position=position,
            )
            if stage.id.uuid in existing:
                await self._session.execute(
                    update(FunnelStageModel)
                    .where(
                        FunnelStageModel.id == stage.id,
                        FunnelStageModel.funnel_id == entity.id,
                    )
                    .values(**values)
                )
            else:
                await self._session.execute(
                    insert(FunnelStageModel).values(
                        id=stage.id, funnel_id=entity.id, **values
                    )
                )

    async def save(self, entity: Funnel) -> None:
        """Записывает изменённое определение без commit."""
        existing = set(
            (
                await self._session.execute(
                    select(FunnelStageModel.id).where(
                        FunnelStageModel.funnel_id == entity.id
                    )
                )
            ).scalars()
        )
        values = FunnelMapper.to_values(entity)
        values.pop("id")
        await self._session.execute(
            update(FunnelModel).where(FunnelModel.id == entity.id).values(**values)
        )
        await self._stages(entity, existing)
        await self._session.execute(
            delete(FunnelStageModel).where(
                FunnelStageModel.funnel_id == entity.id,
                FunnelStageModel.id.not_in([stage.id.uuid for stage in entity.stages]),
            )
        )
