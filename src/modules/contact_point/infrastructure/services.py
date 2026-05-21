from __future__ import annotations

import hashlib
import re

from src.modules.contact_point.application.ports import (
    ContactPointHashPort,
    ContactPointNormalizerPort,
    ContactPointObjectFeatureGatePort,
    OwnerResolverPort,
)
from src.modules.contact_point.domain.binding import OwnerContactPointBinding
from src.modules.contact_point.domain.contact_point import (
    ContactPointTypeVO,
    InvalidContactPointValueError,
    UnsupportedContactPointTypeError,
)
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.schema_registry.application.object_feature.use_case import (
    AssertObjectFeatureEnabledUseCaseProtocol,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.value_object import (
    ObjectFeatureCode,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactPointNormalizeService(ContactPointNormalizerPort):
    def normalize(
        self,
        *,
        contact_point_type: ContactPointTypeVO,
        raw_value: str,
    ) -> str:
        if contact_point_type == ContactPointTypeVO.EMAIL:
            return self._normalize_email(raw_value)
        if contact_point_type == ContactPointTypeVO.PHONE:
            return self._normalize_ukrainian_phone(raw_value)
        raise UnsupportedContactPointTypeError(str(contact_point_type))

    @staticmethod
    def _normalize_email(raw_value: str) -> str:
        value = raw_value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise InvalidContactPointValueError(
                ContactPointTypeVO.EMAIL.value, raw_value
            )
        return value

    @staticmethod
    def _normalize_ukrainian_phone(raw_value: str) -> str:
        digits = "".join(char for char in raw_value if char.isdigit())
        if digits.startswith("380") and len(digits) == 12:
            normalized = f"+{digits}"
        elif digits.startswith("0") and len(digits) == 10:
            normalized = f"+38{digits}"
        elif len(digits) == 9:
            normalized = f"+380{digits}"
        else:
            raise InvalidContactPointValueError(
                ContactPointTypeVO.PHONE.value, raw_value
            )

        if not re.match(r"^\+380\d{9}$", normalized):
            raise InvalidContactPointValueError(
                ContactPointTypeVO.PHONE.value, raw_value
            )
        return normalized


class ContactPointHashService(ContactPointHashPort):
    def hash(self, normalized_value: str) -> str:
        return hashlib.sha256(normalized_value.encode("utf-8")).hexdigest()


class RuntimeOwnerResolver(OwnerResolverPort):
    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway

    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
    ) -> bool:
        descriptor = await self._runtime_object_resolver.resolve_by_id(
            tenant_id=tenant_id,
            object_id=RuntimeObjectIdVO.from_value(owner.owner_object_id.uuid),
        )
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=owner.owner_record_id.uuid,
        )
        return row is not None


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


__all__ = [
    "ContactPointHashService",
    "ContactPointNormalizeService",
    "RuntimeOwnerResolver",
    "SchemaRegistryContactPointObjectFeatureGate",
]
