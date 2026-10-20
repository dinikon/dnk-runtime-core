from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.error import ChannelsConflictError


@dataclass(slots=True)
class ExternalBinding:
    """Историческая связь внешней публикации внутри одного представления."""

    id: EntityIdVO
    publication_id: EntityIdVO
    created_at: datetime
    created_by: EntityIdVO
    released_at: datetime | None
    released_by: EntityIdVO | None

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        publication_id: EntityIdVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт активную связь без изменения исходной публикации."""
        return cls.restore(identifier, publication_id, now, actor, None, None)

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        publication_id: EntityIdVO,
        created_at: datetime,
        created_by: EntityIdVO,
        released_at: datetime | None,
        released_by: EntityIdVO | None,
    ) -> Self:
        """Восстанавливает согласованное состояние истории связи."""
        if any(
            not isinstance(value, EntityIdVO)
            for value in (identifier, publication_id, created_by)
        ) or (released_by is not None and not isinstance(released_by, EntityIdVO)):
            raise ChannelsConflictError("invalid_binding_identity")
        if (released_at is None) != (released_by is None):
            raise ChannelsConflictError("invalid_binding_history")
        return cls(
            identifier, publication_id, created_at, created_by, released_at, released_by
        )

    def release(self, actor: EntityIdVO, now: datetime) -> None:
        """Закрывает активную связь с сохранением аудита."""
        if self.released_at is not None:
            raise ChannelsConflictError("binding_already_released")
        self.released_at, self.released_by = now, actor
