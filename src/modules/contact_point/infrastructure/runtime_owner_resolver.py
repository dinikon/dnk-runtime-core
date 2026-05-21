from __future__ import annotations

from src.modules.contact_point.application.ports import OwnerResolverPort
from src.modules.contact_point.domain.binding import OwnerContactPointBinding
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


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


__all__ = ["RuntimeOwnerResolver"]
