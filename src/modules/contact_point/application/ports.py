from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.domain.binding.value_object import (
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


class OwnerResolverPort(Protocol):
    async def exists(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
    ) -> bool: ...


class ContactPointObjectFeatureGatePort(Protocol):
    async def assert_contact_point_enabled(
        self,
        *,
        tenant_id: EntityIdVO,
        owner_object_id: EntityIdVO,
    ) -> None: ...


class ContactPointNormalizerPort(Protocol):
    def normalize(
        self,
        *,
        contact_point_type: ContactPointTypeVO,
        raw_value: str,
    ) -> str: ...


class ContactPointHashPort(Protocol):
    def hash(self, normalized_value: str) -> str: ...


__all__ = [
    "ContactPointHashPort",
    "ContactPointNormalizerPort",
    "ContactPointObjectFeatureGatePort",
    "OwnerResolverPort",
]
