from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
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


def _entity(
    *,
    kind: ObjectFeatureKind = ObjectFeatureKind.CUSTOM,
    status: ObjectFeatureStatus = ObjectFeatureStatus.DISABLED,
    is_locked: bool = False,
) -> ObjectFeatureConfigEntity:
    now = datetime.now(UTC)
    return ObjectFeatureConfigEntity.create(
        id_=ObjectFeatureConfigIdVO.from_value(uuid4()),
        now=now,
        tenant_id=EntityIdVO.from_value(uuid4()),
        object_id=RuntimeObjectIdVO.from_value(uuid4()),
        feature_code=FeatureCodeVO("CONTACT_POINT"),
        kind=kind,
        status=status,
        config={"enabled": False},
        is_locked=is_locked,
        locked_reason="Seed controlled" if is_locked else None,
    )


class SchemaRegistryObjectFeatureEntityTests(unittest.TestCase):
    def test_enable_changes_status(self) -> None:
        entity = _entity()
        now = entity.updated_at + timedelta(seconds=1)

        entity.enable(now=now)

        self.assertEqual(entity.status, ObjectFeatureStatus.ENABLED)
        self.assertEqual(entity.updated_at, now)

    def test_disable_is_forbidden_for_locked_config(self) -> None:
        entity = _entity(
            status=ObjectFeatureStatus.ENABLED,
            is_locked=True,
        )

        with self.assertRaises(ObjectFeatureConfigLockedError):
            entity.disable(now=datetime.now(UTC))

    def test_disable_is_forbidden_for_non_custom_config(self) -> None:
        entity = _entity(
            kind=ObjectFeatureKind.STANDARD,
            status=ObjectFeatureStatus.ENABLED,
        )

        with self.assertRaises(ObjectFeatureConfigForbiddenError):
            entity.disable(now=datetime.now(UTC))

    def test_assert_enabled_raises_for_disabled_config(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.DISABLED)

        with self.assertRaises(ObjectFeatureNotEnabledError):
            entity.assert_enabled()


__all__ = ["SchemaRegistryObjectFeatureEntityTests"]
