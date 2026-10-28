from uuid import UUID
from collections.abc import Mapping
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.funnel.application.values import StageProjection
from src.modules.funnel.application.port.read_row import FunnelReadRowDTO
from src.modules.funnel.infrastructure.persistence.models.funnel import FunnelModel
from src.modules.funnel.infrastructure.persistence.models.stage import FunnelStageModel


class SqlAlchemyFunnelQueryRepository:
    """Пакетно читает процессы и стадии для UI."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию UoW."""
        self._session = session

    async def _rows(
        self, rows: list[Mapping[str, Any]]
    ) -> tuple[FunnelReadRowDTO, ...]:
        """Собирает определения без N+1."""
        ids = [r["id"] for r in rows]
        by_id = {}
        stages = (
            (
                await self._session.execute(
                    select(FunnelStageModel.__table__)
                    .where(FunnelStageModel.funnel_id.in_(ids))
                    .order_by(FunnelStageModel.position)
                )
            )
            .mappings()
            .all()
            if ids
            else []
        )
        for s in stages:
            by_id.setdefault(s["funnel_id"], []).append(
                StageProjection(
                    s["id"], s["name"], s["color"], s["position"], s["kind"]
                )
            )
        return tuple(
            FunnelReadRowDTO(
                **{
                    k: r[k]
                    for k in (
                        "id",
                        "model_key",
                        "name",
                        "is_default",
                        "revision",
                        "created_at",
                        "updated_at",
                    )
                },
                stages=tuple(by_id.get(r["id"], [])),
            )
            for r in rows
        )

    async def get(self, funnel_id: UUID) -> FunnelReadRowDTO | None:
        """Возвращает проекцию определения."""
        row = (
            (
                await self._session.execute(
                    select(FunnelModel.__table__).where(FunnelModel.id == funnel_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        return (await self._rows([row]))[0] if row else None

    async def list(
        self, model_key: str | None, search: str, offset: int, limit: int
    ) -> tuple[tuple[FunnelReadRowDTO, ...], int]:
        """Возвращает фильтрованную страницу, default первым."""
        conditions = []
        if model_key:
            conditions.append(FunnelModel.model_key == model_key)
        if search:
            conditions.append(FunnelModel.name.icontains(search, autoescape=True))
        total = (
            await self._session.execute(
                select(func.count()).select_from(FunnelModel).where(*conditions)
            )
        ).scalar_one()
        rows = (
            (
                await self._session.execute(
                    select(FunnelModel.__table__)
                    .where(*conditions)
                    .order_by(
                        FunnelModel.is_default.desc(), FunnelModel.name, FunnelModel.id
                    )
                    .offset(offset)
                    .limit(limit)
                )
            )
            .mappings()
            .all()
        )
        return await self._rows(list(rows)), total
