from dataclasses import dataclass
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.domain.error import FunnelError


@dataclass(frozen=True, slots=True)
class Stage:
    """Внутренняя стадия процесса со стабильным идентификатором."""

    id: EntityIdVO
    name: str
    color: str

    @classmethod
    def create(cls, *, stage_id: EntityIdVO, name: str, color: str = "neutral") -> Self:
        """Проверяет название и семантический цвет."""
        name = name.strip()
        if (
            not name
            or len(name) > 100
            or color not in ("neutral", "blue", "green", "amber", "red", "violet")
        ):
            raise FunnelError("Некорректное название или цвет стадии.")
        return cls(EntityIdVO.from_value(stage_id), name, color)

    @classmethod
    def restore(cls, *, stage_id: EntityIdVO, name: str, color: str) -> Self:
        """Восстанавливает проверенную стадию."""
        return cls.create(stage_id=stage_id, name=name, color=color)
