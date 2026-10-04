from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateSkuCommand:
    """Создание учётной позиции от имени доверенного actor."""

    actor_id: EntityIdVO
    code: str
    title: str
