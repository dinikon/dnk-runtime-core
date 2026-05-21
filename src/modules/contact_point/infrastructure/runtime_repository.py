from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.contact_point.domain.binding import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    ContactPointBindingNotFoundError,
    ContactPointBindingRepositoryProtocol,
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.contact_point import (
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointNotFoundError,
    ContactPointRepositoryProtocol,
    ContactPointTypeVO,
)
from src.modules.contact_point.infrastructure.row_mapper import (
    contact_point_binding_entity,
    contact_point_entity,
)
from src.modules.contact_point.infrastructure.runtime_object_names import (
    _CONTACT_POINT,
    _CONTACT_POINT_BINDING,
)
from src.modules.runtime_data.application.models import (
    PageSpec,
    SortSpec,
    TypedFilterExpression,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO


class ContactPointRuntimeRepository(
    ContactPointRepositoryProtocol,
    ContactPointBindingRepositoryProtocol,
):
    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def load_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_id: ContactPointIdVO,
    ) -> ContactPointEntity | None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_point_id.uuid,
        )
        return None if row is None else contact_point_entity(row)

    async def load_binding(
        self,
        *,
        tenant_id: EntityIdVO,
        binding_id: ContactPointBindingIdVO,
    ) -> ContactPointBindingEntity | None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=binding_id.uuid,
        )
        return None if row is None else contact_point_binding_entity(row)

    async def get_by_type_and_hash(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_type: ContactPointTypeVO,
        hash_value: str,
    ) -> ContactPointEntity | None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="contact_point_type",
                    op="eq",
                    value=contact_point_type.value,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="normalized_hash",
                    op="eq",
                    value=hash_value,
                ),
            ),
            limit=1,
        )
        return None if not rows else contact_point_entity(rows[0])

    async def save_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point: ContactPointEntity,
    ) -> ContactPointEntity:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_point.id.uuid,
        )
        payload = {
            "contact_point_type": contact_point.contact_point_type.value,
            "raw_value": contact_point.raw_value,
            "display_value": contact_point.display_value,
            "normalized_value": contact_point.normalized_value,
            "normalized_hash": contact_point.hash_value,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": contact_point.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=contact_point.id.uuid,
                patch=payload,
            )
            if row is None:
                raise ContactPointNotFoundError(str(contact_point.id))
        return contact_point_entity(row)

    async def find_by_owner_and_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_id: ContactPointIdVO,
    ) -> ContactPointBindingEntity | None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                *self._owner_filters(descriptor, owner),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="contact_point_id",
                    op="eq",
                    value=contact_point_id.uuid,
                ),
            ),
            limit=1,
        )
        return None if not rows else contact_point_binding_entity(rows[0])

    async def find_first_active_by_owner_and_type(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> ContactPointBindingEntity | None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        rows = await self._list(
            descriptor=descriptor,
            filters=self._active_owner_type_filters(
                descriptor=descriptor,
                owner=owner,
                contact_point_type=contact_point_type,
            ),
            sorting=(SortSpec("created_at"), SortSpec("id")),
            limit=1,
        )
        return None if not rows else contact_point_binding_entity(rows[0])

    async def unset_primary_for_owner_and_type(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
        exclude_binding_id: ContactPointBindingIdVO | None = None,
    ) -> None:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        filters: list[TypedFilterExpression] = [
            *self._active_owner_type_filters(
                descriptor=descriptor,
                owner=owner,
                contact_point_type=contact_point_type,
            ),
            self._filter_builder.condition(
                descriptor=descriptor,
                field="is_primary",
                op="eq",
                value=True,
            ),
        ]
        if exclude_binding_id is not None:
            filters.append(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="id",
                    op="neq",
                    value=exclude_binding_id.uuid,
                )
            )
        await self._runtime_command_gateway.update_where(
            descriptor=descriptor,
            filters=tuple(filters),
            patch={"is_primary": False},
        )

    async def has_active_bindings_for_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_id: ContactPointIdVO,
    ) -> bool:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        rows = await self._list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="contact_point_id",
                    op="eq",
                    value=contact_point_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="is_active",
                    op="eq",
                    value=True,
                ),
            ),
            limit=1,
        )
        return bool(rows)

    async def save_binding(
        self,
        *,
        tenant_id: EntityIdVO,
        binding: ContactPointBindingEntity,
    ) -> ContactPointBindingEntity:
        descriptor = await self._resolve_descriptor(tenant_id, _CONTACT_POINT_BINDING)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=binding.id.uuid,
        )
        payload = {
            "contact_point_id": binding.contact_point_id.uuid,
            "contact_point_type": binding.contact_point_type.value,
            "owner_object_id": binding.owner.owner_object_id.uuid,
            "owner_record_id": binding.owner.owner_record_id.uuid,
            "is_primary": binding.is_primary,
            "detached_at": binding.detached_at,
            "is_active": binding.is_active,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": binding.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=binding.id.uuid,
                patch=payload,
            )
            if row is None:
                raise ContactPointBindingNotFoundError(str(binding.id))
        return contact_point_binding_entity(row)

    def _owner_filters(
        self,
        descriptor: RuntimeObjectDescriptor,
        owner: OwnerContactPointBinding,
    ) -> tuple[TypedFilterExpression, TypedFilterExpression]:
        return (
            self._filter_builder.condition(
                descriptor=descriptor,
                field="owner_object_id",
                op="eq",
                value=owner.owner_object_id.uuid,
            ),
            self._filter_builder.condition(
                descriptor=descriptor,
                field="owner_record_id",
                op="eq",
                value=owner.owner_record_id.uuid,
            ),
        )

    def _active_owner_type_filters(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> tuple[TypedFilterExpression, ...]:
        return (
            *self._owner_filters(descriptor, owner),
            self._filter_builder.condition(
                descriptor=descriptor,
                field="contact_point_type",
                op="eq",
                value=contact_point_type.value,
            ),
            self._filter_builder.condition(
                descriptor=descriptor,
                field="is_active",
                op="eq",
                value=True,
            ),
        )

    async def _list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        limit: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=filters,
            sorting=sorting,
            page=PageSpec(limit=limit, offset=0) if limit is not None else None,
        )

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


__all__ = ["ContactPointRuntimeRepository"]
