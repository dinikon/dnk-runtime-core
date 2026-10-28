from dataclasses import dataclass
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.domain.error import FunnelError
from src.modules.funnel.domain.stage_kind import StageKind
from src.modules.funnel.domain.value_object.stage_color import StageColorVO


@dataclass(frozen=True, slots=True)
class Stage:
    """Внутренняя стадия со стабильными идентификатором и назначением."""

    id: EntityIdVO
    name: str
    color: StageColorVO
    kind: StageKind

    @classmethod
    def create(
        cls,
        *,
        stage_id: EntityIdVO,
        name: str,
        color: str = "#64748B",
        kind: str = "in_progress",
    ) -> Self:
        """Проверяет собственные значения новой стадии."""
        name = name.strip()
        if not name or len(name) > 100:
            raise FunnelError("Некорректное название стадии.")
        try:
            stage_kind = StageKind(kind)
        except ValueError as exc:
            raise FunnelError("Неизвестный тип стадии.") from exc
        return cls(
            EntityIdVO.from_value(stage_id), name, StageColorVO(color), stage_kind
        )

    @classmethod
    def restore(cls, *, stage_id: EntityIdVO, name: str, color: str, kind: str) -> Self:
        """Восстанавливает собственные значения сохранённой стадии."""
        return cls.create(stage_id=stage_id, name=name, color=color, kind=kind)
