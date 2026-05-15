from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from src.modules.runtime_data.application.ports import RuntimeRelationCommandGateway
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class _RuntimeRelationUseCaseBase:
    """Base class для runtime relation use cases."""

    def __init__(
        self,
        *,
        resolver: RuntimeObjectResolverProtocol,
        gateway: RuntimeRelationCommandGateway,
    ) -> None:
        """Инициализирует use case resolver-ом и relation gateway."""
        self._resolver = resolver
        self._gateway = gateway


class GetRelatedRecordUseCase(_RuntimeRelationUseCaseBase):
    """Use case чтения single related record."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
    ) -> Mapping[str, Any] | None:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        return await self._gateway.get_related_record(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
        )


class ListRelatedRecordsUseCase(_RuntimeRelationUseCaseBase):
    """Use case чтения related records collection."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
    ) -> list[Mapping[str, Any]]:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        return await self._gateway.list_related_records(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
        )


class AttachRelatedRecordUseCase(_RuntimeRelationUseCaseBase):
    """Use case attach M2M related record."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        await self._gateway.attach_related_record(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
            related_id=related_id,
        )


class DetachRelatedRecordUseCase(_RuntimeRelationUseCaseBase):
    """Use case detach M2M related record."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        await self._gateway.detach_related_record(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
            related_id=related_id,
        )


class SetRelationUseCase(_RuntimeRelationUseCaseBase):
    """Use case set FK relation."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
        related_id: Any,
    ) -> None:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        await self._gateway.set_relation(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
            related_id=related_id,
        )


class UnsetRelationUseCase(_RuntimeRelationUseCaseBase):
    """Use case unset FK relation."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        relation_name: str,
        object_id: Any,
        related_id: Any | None = None,
    ) -> None:
        descriptor = await self._resolver.resolve(tenant_id, object_name)
        await self._gateway.unset_relation(
            descriptor=descriptor,
            relation_name=relation_name,
            object_id=object_id,
            related_id=related_id,
        )


__all__ = [
    "AttachRelatedRecordUseCase",
    "DetachRelatedRecordUseCase",
    "GetRelatedRecordUseCase",
    "ListRelatedRecordsUseCase",
    "SetRelationUseCase",
    "UnsetRelationUseCase",
]
