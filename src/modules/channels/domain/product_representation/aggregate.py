from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.entity.external_binding import (
    ExternalBinding,
)
from src.modules.channels.domain.error import ChannelsConflictError


@dataclass(slots=True)
class ProductRepresentation:
    """Владеет основной привязкой товара одного подключения и её историей."""

    id: EntityIdVO
    connection_id: EntityIdVO
    catalog_item_id: EntityIdVO
    revision: int
    bindings: list[ExternalBinding]

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        catalog_item_id: EntityIdVO,
    ) -> Self:
        """Создаёт представление без активной привязки."""
        return cls.restore(identifier, connection_id, catalog_item_id, 1, [])

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        catalog_item_id: EntityIdVO,
        revision: int,
        bindings: list[ExternalBinding],
    ) -> Self:
        """Проверяет инварианты восстановления в Domain, а не mapper."""
        if (
            any(
                not isinstance(value, EntityIdVO)
                for value in (identifier, connection_id, catalog_item_id)
            )
            or type(revision) is not int
            or revision < 1
            or sum(b.released_at is None for b in bindings) > 1
            or len({b.id for b in bindings}) != len(bindings)
        ):
            raise ChannelsConflictError("invalid_representation_state")
        return cls(identifier, connection_id, catalog_item_id, revision, list(bindings))

    def active_binding(self) -> ExternalBinding | None:
        """Возвращает основную действующую связь текущего представления."""
        return next((b for b in self.bindings if b.released_at is None), None)

    def bind(
        self,
        binding_id: EntityIdVO,
        publication_id: EntityIdVO,
        connection_id: EntityIdVO,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> ExternalBinding:
        """Отклоняет устаревшую версию или вторую активную основную публикацию."""
        if connection_id != self.connection_id:
            raise ChannelsConflictError("publication_connection_mismatch")
        if any(binding.id == binding_id for binding in self.bindings):
            raise ChannelsConflictError("duplicate_binding_id")
        if expected_revision != self.revision:
            raise ChannelsConflictError("binding_revision_conflict")
        if self.active_binding() is not None:
            raise ChannelsConflictError("catalog_item_already_bound")
        binding = ExternalBinding.create(binding_id, publication_id, actor, now)
        self.bindings.append(binding)
        self.revision += 1
        return binding

    def unbind(
        self,
        binding_id: EntityIdVO,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Снимает только указанную связь и защищает от устаревшего диалога."""
        binding = self.active_binding()
        if (
            self.revision != expected_revision
            or binding is None
            or binding.id != binding_id
        ):
            raise ChannelsConflictError("binding_revision_conflict")
        binding.release(actor, now)
        self.revision += 1
