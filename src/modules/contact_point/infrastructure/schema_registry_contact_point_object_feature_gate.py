from __future__ import annotations

from src.modules.contact_point.application.ports import (
    ContactPointObjectFeatureGatePort,
)
from src.modules.schema_registry.application.object_feature.use_case import (
    AssertObjectFeatureEnabledUseCaseProtocol,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.value_object import (
    ObjectFeatureCode,
)
from src.modules.shared import EntityIdVO


class SchemaRegistryContactPointObjectFeatureGate(ContactPointObjectFeatureGatePort):
    def __init__(
        self,
        assert_object_feature_enabled: AssertObjectFeatureEnabledUseCaseProtocol,
    ) -> None:
        self._assert_object_feature_enabled = assert_object_feature_enabled

    async def assert_contact_point_enabled(
        self,
        *,
        tenant_id: EntityIdVO,
        owner_object_id: EntityIdVO,
    ) -> None:
        await self._assert_object_feature_enabled(
            tenant_id=tenant_id,
            object_id=RuntimeObjectIdVO.from_value(owner_object_id.uuid),
            feature_code=ObjectFeatureCode.CONTACT_POINT.value,
        )


__all__ = ["SchemaRegistryContactPointObjectFeatureGate"]
