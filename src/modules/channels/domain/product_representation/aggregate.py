from dataclasses import dataclass
from datetime import datetime

from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ProductRepresentation:
    """Владеет overrides, разрешением экспорта, ревизией и аудитом одной группы."""

    id: EntityIdVO
    binding_group_id: EntityIdVO
    revision: int
    export_enabled: bool
    overrides: RepresentationOverridesVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        binding_group_id: EntityIdVO,
        overrides: RepresentationOverridesVO,
        actor: EntityIdVO,
        now: datetime,
    ) -> "ProductRepresentation":
        """Создаёт первую сохранённую ревизию с запрещённым экспортом."""
        return cls.restore(
            identifier=identifier,
            binding_group_id=binding_group_id,
            revision=1,
            export_enabled=False,
            overrides=overrides,
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
        binding_group_id: EntityIdVO,
        revision: int,
        export_enabled: bool,
        overrides: RepresentationOverridesVO,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> "ProductRepresentation":
        """Восстанавливает проверенное состояние без исправления повреждённой записи."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (identifier, binding_group_id, created_by, updated_by)
            )
            or type(revision) is not int
            or revision < 1
            or type(export_enabled) is not bool
            or not isinstance(overrides, RepresentationOverridesVO)
        ):
            raise ProductRepresentationError("representation_state_invalid")
        if (
            any(
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
                for value in (created_at, updated_at)
            )
            or updated_at < created_at
        ):
            raise ProductRepresentationError("representation_audit_invalid")
        return cls(
            identifier,
            binding_group_id,
            revision,
            export_enabled,
            overrides,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def require_revision(self, expected_revision: int) -> None:
        """Проверяет ревизию до сравнения значений и изменения состояния."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ProductRepresentationError(
                "representation_revision_conflict", conflict=True
            )

    def change_overrides(
        self,
        *,
        overrides: RepresentationOverridesVO,
        expected_revision: int,
        export_ready: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет контент и при необходимости выключает экспорт одним переходом."""
        self.require_revision(expected_revision)
        enabled = self.export_enabled and export_ready
        if self.overrides == overrides and self.export_enabled == enabled:
            return
        self._change(overrides=overrides, export_enabled=enabled, actor=actor, now=now)

    def enable_export(
        self,
        *,
        expected_revision: int,
        blockers: tuple[str, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Разрешает экспорт только после новой проверки текущего представления."""
        self.require_revision(expected_revision)
        if blockers:
            raise ProductRepresentationError(blockers[0])
        if not self.export_enabled:
            self._change(
                overrides=self.overrides, export_enabled=True, actor=actor, now=now
            )

    def disable_export(
        self, *, expected_revision: int, actor: EntityIdVO, now: datetime
    ) -> None:
        """Идемпотентно запрещает экспорт без проверки готовности контента."""
        self.require_revision(expected_revision)
        if self.export_enabled:
            self._change(
                overrides=self.overrides, export_enabled=False, actor=actor, now=now
            )

    def reconcile_binding_items(
        self, *, retained_ids: tuple[EntityIdVO, ...], actor: EntityIdVO, now: datetime
    ) -> None:
        """После изменения состава сохраняет живые overrides и аннулирует разрешение."""
        if any(not isinstance(identifier, EntityIdVO) for identifier in retained_ids):
            raise ProductRepresentationError("representation_item_invalid")
        overrides = RepresentationOverridesVO(
            self.overrides.common,
            tuple(
                value
                for value in self.overrides.items
                if value.binding_item_id in retained_ids
            ),
        )
        self._change(overrides=overrides, export_enabled=False, actor=actor, now=now)

    def _change(
        self,
        *,
        overrides: RepresentationOverridesVO,
        export_enabled: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Проверяет весь кандидат до единственного изменения ревизии и аудита."""
        candidate = self.restore(
            identifier=self.id,
            binding_group_id=self.binding_group_id,
            revision=self.revision + 1,
            export_enabled=export_enabled,
            overrides=overrides,
            created_at=self.created_at,
            updated_at=now,
            created_by=self.created_by,
            updated_by=actor,
        )
        self.overrides = candidate.overrides
        self.export_enabled = candidate.export_enabled
        self.revision = candidate.revision
        self.updated_at = candidate.updated_at
        self.updated_by = candidate.updated_by
