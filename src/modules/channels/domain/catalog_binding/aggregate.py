from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.catalog_binding.value_object import BindingMode


@dataclass(slots=True)
class CatalogBindingGroup:
    """Владеет сопоставлениями одной карточки, режима и подключения."""

    id: EntityIdVO
    connection_id: EntityIdVO
    catalog_root_id: EntityIdVO
    mode: BindingMode
    publication_root_id: EntityIdVO | None
    revision: int
    items: tuple[CatalogBindingItem, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        catalog_root_id: EntityIdVO,
        mode: BindingMode,
        publication_root_id: EntityIdVO | None,
        items: tuple[CatalogBindingItem, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> "CatalogBindingGroup":
        """Создаёт непустую группу с первой ревизией."""
        return cls.restore(
            identifier=identifier,
            connection_id=connection_id,
            catalog_root_id=catalog_root_id,
            mode=mode,
            publication_root_id=publication_root_id,
            revision=1,
            items=items,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        catalog_root_id: EntityIdVO,
        mode: BindingMode,
        publication_root_id: EntityIdVO | None,
        revision: int,
        items: tuple[CatalogBindingItem, ...],
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> "CatalogBindingGroup":
        """Проверяет собственные инварианты; внешний конфликт не мешает чтению."""
        if (
            not all(
                isinstance(v, EntityIdVO)
                for v in (identifier, connection_id, created_by, updated_by)
            )
            or not isinstance(catalog_root_id, EntityIdVO)
            or not isinstance(mode, BindingMode)
            or type(revision) is not int
            or revision < 1
        ):
            raise CatalogBindingError("binding_invalid")
        if (mode is BindingMode.VARIABLE_TO_SIMPLE) != (
            publication_root_id is None
        ) or (
            publication_root_id is not None
            and not isinstance(publication_root_id, EntityIdVO)
        ):
            raise CatalogBindingError("binding_root_invalid")
        if (
            any(
                not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None
                for v in (created_at, updated_at)
            )
            or updated_at < created_at
        ):
            raise CatalogBindingError("binding_audit_invalid")
        if not items:
            raise CatalogBindingError("binding_items_empty")
        if mode is BindingMode.SIMPLE_TO_SIMPLE and len(items) != 1:
            raise CatalogBindingError("binding_simple_structure_invalid")
        if (
            any(not isinstance(v, CatalogBindingItem) for v in items)
            or len({v.id for v in items}) != len(items)
            or len({v.catalog_position_id for v in items}) != len(items)
            or len({v.publication_id for v in items}) != len(items)
        ):
            raise CatalogBindingError("binding_position_duplicate")
        return cls(
            identifier,
            connection_id,
            catalog_root_id,
            mode,
            publication_root_id,
            revision,
            tuple(sorted(items, key=lambda v: str(v.catalog_position_id))),
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def require_revision(self, expected: int) -> None:
        """Не позволяет позднему редактору перезаписать чужие изменения."""
        if type(expected) is not int or expected != self.revision:
            raise CatalogBindingError("binding_revision_conflict", conflict=True)

    def change_items(
        self,
        *,
        items: tuple[CatalogBindingItem, ...],
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет полный набор после проверки кандидата, сохраняя неизменные якоря."""
        self.require_revision(expected_revision)
        candidate = self.restore(
            identifier=self.id,
            connection_id=self.connection_id,
            catalog_root_id=self.catalog_root_id,
            mode=self.mode,
            publication_root_id=self.publication_root_id,
            revision=self.revision,
            items=items,
            created_at=self.created_at,
            updated_at=now,
            created_by=self.created_by,
            updated_by=actor,
        )
        before = {(v.catalog_position_id, v.publication_id) for v in self.items}
        after = {(v.catalog_position_id, v.publication_id) for v in candidate.items}
        if before != after:
            self.items, self.updated_at, self.updated_by = candidate.items, now, actor
            self.revision += 1
