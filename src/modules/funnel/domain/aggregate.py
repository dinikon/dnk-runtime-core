from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.domain.stage import Stage
from src.modules.funnel.domain.stage_kind import StageKind
from src.modules.funnel.domain.error import (
    FunnelError,
    FunnelConflictError,
    FunnelNotFoundError,
)


@dataclass(slots=True)
class Funnel:
    """Определение процесса без объектов CRM и автоматизаций."""

    id: EntityIdVO
    model_key: str
    name: str
    stages: tuple[Stage, ...]
    is_default: bool
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @staticmethod
    def _validate(model_key: str, name: str, stages: tuple[Stage, ...]) -> None:
        """Проверяет целостность полного определения."""
        if (
            model_key not in ("crm.lead", "crm.deal")
            or not name.strip()
            or len(name) > 150
        ):
            raise FunnelError("Некорректный тип или название воронки.")
        if not 3 <= len(stages) <= 50 or len({s.id for s in stages}) != len(stages):
            raise FunnelError("Нужны 3–50 стадий с уникальными ID.")
        kinds = [stage.kind for stage in stages]
        if (
            kinds.count(StageKind.WON) != 1
            or StageKind.LOST not in kinds
            or StageKind.IN_PROGRESS not in kinds
        ):
            raise FunnelError(
                "Нужны рабочая, ровно одна успешная и хотя бы одна неуспешная стадия."
            )
        order = {StageKind.IN_PROGRESS: 0, StageKind.WON: 1, StageKind.LOST: 2}
        if kinds != sorted(kinds, key=order.__getitem__):
            raise FunnelError("Порядок групп: в работе, успешная, неуспешные.")

    @classmethod
    def create(
        cls,
        *,
        funnel_id: EntityIdVO,
        model_key: str,
        name: str,
        stages: tuple[Stage, ...],
        actor_id: EntityIdVO,
        now: datetime,
        is_default: bool = False,
    ) -> Self:
        """Создаёт полный проверенный процесс."""
        name = name.strip()
        cls._validate(model_key, name, stages)
        return cls(
            EntityIdVO.from_value(funnel_id),
            model_key,
            name,
            stages,
            is_default,
            1,
            now,
            now,
            EntityIdVO.from_value(actor_id),
            EntityIdVO.from_value(actor_id),
        )

    @staticmethod
    def default_stages(stage_ids: tuple[EntityIdVO, ...]) -> tuple[Stage, ...]:
        """Собирает стандартный процесс из предоставленных извне ID."""
        if len(stage_ids) != 4:
            raise FunnelError("Для шаблона нужны четыре ID.")
        return tuple(
            Stage.create(stage_id=stage_id, name=name, color=color, kind=kind)
            for stage_id, (name, color, kind) in zip(
                stage_ids,
                (
                    ("Новый", "#3B82F6", "in_progress"),
                    ("В работе", "#06B6D4", "in_progress"),
                    ("Успешный", "#84CC16", "won"),
                    ("Неудачный", "#EF4444", "lost"),
                ),
                strict=True,
            )
        )

    @classmethod
    def restore(cls, **values: object) -> Self:
        """Восстанавливает процесс с сохранением ID и версии."""
        values = dict(values)
        for key in ("id", "created_by", "updated_by"):
            values[key] = EntityIdVO.from_value(values[key])
        result = cls(**values)
        cls._validate(result.model_key, result.name, result.stages)
        if result.revision < 1:
            raise FunnelError("Некорректная версия процесса.")
        return result

    def replace_process(
        self,
        *,
        name: str,
        stages: tuple[Stage, ...],
        expected_revision: int,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Атомарно проверяет определение, сохраняя назначение и успешную стадию."""
        if expected_revision != self.revision:
            raise FunnelConflictError("Воронка изменена. Сверьте актуальные стадии.")
        name = name.strip()
        self._validate(self.model_key, name, stages)
        previous = {stage.id: stage for stage in self.stages}
        current = {stage.id: stage for stage in stages}
        for stage in stages:
            if stage.id in previous and stage.kind != previous[stage.id].kind:
                raise FunnelError("Тип сохранённой стадии изменить нельзя.")
        if any(
            stage.kind is StageKind.WON and stage.id not in current
            for stage in self.stages
        ):
            raise FunnelError("Успешную стадию нельзя удалить или заменить.")
        if (name, stages) == (self.name, self.stages):
            return
        self.name = name
        self.stages = stages
        self.revision += 1
        self.updated_at = now
        self.updated_by = EntityIdVO.from_value(actor_id)

    def select_stage(self, model_key: str, stage_id: EntityIdVO | None = None) -> Stage:
        """Проверяет тип владельца и принадлежность стадии."""
        if model_key != self.model_key:
            raise FunnelError("Воронка другого типа.")
        if stage_id is None:
            return self.stages[0]
        for stage in self.stages:
            if stage.id == EntityIdVO.from_value(stage_id):
                return stage
        raise FunnelNotFoundError("Стадия не принадлежит воронке.")
