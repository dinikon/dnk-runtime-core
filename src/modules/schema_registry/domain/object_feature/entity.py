from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigForbiddenError,
    ObjectFeatureConfigLockedError,
    ObjectFeatureNotEnabledError,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureConfigIdVO,
    ObjectFeatureKind,
    ObjectFeatureStatus,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ObjectFeatureConfigEntity:
    """Доменная сущность feature config runtime-объекта."""

    id: ObjectFeatureConfigIdVO
    created_at: datetime
    updated_at: datetime

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO

    feature_code: FeatureCodeVO
    kind: ObjectFeatureKind
    status: ObjectFeatureStatus
    config: dict[str, Any]
    is_locked: bool
    locked_reason: str | None

    @classmethod
    def create(
        cls,
        *,
        id_: ObjectFeatureConfigIdVO,
        now: datetime,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: FeatureCodeVO,
        kind: ObjectFeatureKind = ObjectFeatureKind.CUSTOM,
        status: ObjectFeatureStatus = ObjectFeatureStatus.DISABLED,
        config: Mapping[str, Any] | None = None,
        is_locked: bool = False,
        locked_reason: str | None = None,
    ) -> Self:
        """Создает object feature config с нормализованным config/lock reason."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            object_id=object_id,
            feature_code=feature_code,
            kind=kind,
            status=status,
            config=dict(config or {}),
            is_locked=is_locked,
            locked_reason=cls._normalize_locked_reason(locked_reason),
        )

    def enable(self, *, now: datetime) -> None:
        """Включает feature config, если он не locked."""
        self._ensure_not_locked()
        self.status = ObjectFeatureStatus.ENABLED
        self.updated_at = now

    def disable(self, *, now: datetime) -> None:
        """Выключает feature config, если он не locked."""
        self._ensure_not_locked()
        self._ensure_user_mutable()
        self.status = ObjectFeatureStatus.DISABLED
        self.updated_at = now

    def update_config(
        self,
        *,
        now: datetime,
        config: Mapping[str, Any],
    ) -> None:
        """Полностью заменяет config, если feature config не locked."""
        self._ensure_not_locked()
        self._ensure_user_mutable()
        self.config = dict(config)
        self.updated_at = now

    def lock(self, *, now: datetime, reason: str | None = None) -> None:
        """Переводит feature config в locked-состояние."""
        self.is_locked = True
        self.locked_reason = self._normalize_locked_reason(reason)
        self.updated_at = now

    def unlock(self, *, now: datetime) -> None:
        """Снимает locked-состояние и очищает reason."""
        self.is_locked = False
        self.locked_reason = None
        self.updated_at = now

    def assert_enabled(self) -> None:
        """Проверяет, что feature config включен."""
        if self.status != ObjectFeatureStatus.ENABLED:
            raise ObjectFeatureNotEnabledError(
                f"Object feature '{self.feature_code.value}' is not enabled."
            )

    def _ensure_not_locked(self) -> None:
        """Проверяет, что feature config можно изменять."""
        if self.is_locked:
            suffix = (
                f" Reason: {self.locked_reason}."
                if self.locked_reason is not None
                else ""
            )
            raise ObjectFeatureConfigLockedError(
                f"Object feature '{self.feature_code.value}' is locked.{suffix}"
            )

    def _ensure_user_mutable(self) -> None:
        """Проверяет, что пользователь может менять feature config."""
        if self.kind != ObjectFeatureKind.CUSTOM:
            raise ObjectFeatureConfigForbiddenError(
                "Only custom object features can be changed by user operations."
            )

    @staticmethod
    def _normalize_locked_reason(value: str | None) -> str | None:
        """Нормализует nullable lock reason."""
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
