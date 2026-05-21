from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.command import AttachContactPointCommand
from src.modules.contact_point.application.dto import AttachContactPointResultDTO
from src.modules.contact_point.application.ports import (
    ContactPointHashPort,
    ContactPointNormalizerPort,
    ContactPointObjectFeatureGatePort,
    OwnerResolverPort,
)
from src.modules.contact_point.domain.binding import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    ContactPointBindingRepositoryProtocol,
    ContactPointOwnerNotFoundError,
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.contact_point import (
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointRepositoryProtocol,
)
from src.modules.shared.kernel.time.ports import ClockPort
from src.modules.shared.kernel.uuid import UuidPort


class AttachContactPointUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: AttachContactPointCommand,
    ) -> AttachContactPointResultDTO: ...


class AttachContactPointUseCase:

    def __init__(
        self,
        *,
        contact_points: ContactPointRepositoryProtocol,
        bindings: ContactPointBindingRepositoryProtocol,
        owner_resolver: OwnerResolverPort,
        feature_gate: ContactPointObjectFeatureGatePort,
        normalizer: ContactPointNormalizerPort,
        hash_service: ContactPointHashPort,
        uuid_generator: UuidPort,
        clock: ClockPort,
    ) -> None:
        self._contact_points = contact_points
        self._bindings = bindings
        self._owner_resolver = owner_resolver
        self._feature_gate = feature_gate
        self._normalizer = normalizer
        self._hash_service = hash_service
        self._uuid_generator = uuid_generator
        self._clock = clock

    async def __call__(
        self,
        command: AttachContactPointCommand,
    ) -> AttachContactPointResultDTO:
        owner = OwnerContactPointBinding(
            owner_object_id=command.owner_object_id,
            owner_record_id=command.owner_record_id,
        )
        owner_exists = await self._owner_resolver.exists(
            tenant_id=command.tenant_id,
            owner=owner,
        )
        if not owner_exists:
            raise ContactPointOwnerNotFoundError(
                str(command.owner_object_id),
                str(command.owner_record_id),
            )

        await self._feature_gate.assert_contact_point_enabled(
            tenant_id=command.tenant_id,
            owner_object_id=command.owner_object_id,
        )

        normalized_value = self._normalizer.normalize(
            contact_point_type=command.contact_point_type,
            raw_value=command.raw_value,
        )
        hash_value = self._hash_service.hash(normalized_value)

        contact_point = await self._contact_points.get_by_type_and_hash(
            tenant_id=command.tenant_id,
            contact_point_type=command.contact_point_type,
            hash_value=hash_value,
        )
        contact_point_created = False
        now = self._clock.now()
        if contact_point is None:
            contact_point = ContactPointEntity.create(
                id_=ContactPointIdVO.from_value(self._uuid_generator.new_uuid()),
                now=now,
                contact_point_type=command.contact_point_type,
                raw_value=command.raw_value,
                normalized_value=normalized_value,
                hash_value=hash_value,
            )
            contact_point = await self._contact_points.save_contact_point(
                tenant_id=command.tenant_id,
                contact_point=contact_point,
            )
            contact_point_created = True

        binding = await self._bindings.find_by_owner_and_contact_point(
            tenant_id=command.tenant_id,
            owner=owner,
            contact_point_id=contact_point.id,
        )
        active_primary = await self._bindings.find_active_primary_by_owner_and_type(
            tenant_id=command.tenant_id,
            owner=owner,
            contact_point_type=command.contact_point_type,
        )
        if binding is not None and binding.is_active:
            should_be_primary = command.is_primary or active_primary is None
            if should_be_primary and not binding.is_primary:
                await self._bindings.unset_primary_for_owner_and_type(
                    tenant_id=command.tenant_id,
                    owner=owner,
                    contact_point_type=command.contact_point_type,
                    exclude_binding_id=binding.id,
                )
                binding.mark_primary(now=now)
                binding = await self._bindings.save_binding(
                    tenant_id=command.tenant_id,
                    binding=binding,
                )
            elif command.is_primary and binding.is_primary:
                await self._bindings.unset_primary_for_owner_and_type(
                    tenant_id=command.tenant_id,
                    owner=owner,
                    contact_point_type=command.contact_point_type,
                    exclude_binding_id=binding.id,
                )
            return AttachContactPointResultDTO(
                contact_point_id=contact_point.id.uuid,
                binding_id=binding.id.uuid,
                contact_point_created=contact_point_created,
                binding_created=False,
                already_attached=True,
            )

        should_be_primary = command.is_primary or active_primary is None
        if should_be_primary:
            await self._bindings.unset_primary_for_owner_and_type(
                tenant_id=command.tenant_id,
                owner=owner,
                contact_point_type=command.contact_point_type,
            )

        if binding is not None:
            binding.reactivate(now=now, is_primary=should_be_primary)
            binding = await self._bindings.save_binding(
                tenant_id=command.tenant_id,
                binding=binding,
            )
            return AttachContactPointResultDTO(
                contact_point_id=contact_point.id.uuid,
                binding_id=binding.id.uuid,
                contact_point_created=contact_point_created,
                binding_created=False,
                already_attached=False,
            )

        binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(self._uuid_generator.new_uuid()),
            now=now,
            contact_point_id=contact_point.id,
            contact_point_type=command.contact_point_type,
            owner=owner,
            is_primary=should_be_primary,
        )
        binding = await self._bindings.save_binding(
            tenant_id=command.tenant_id,
            binding=binding,
        )
        return AttachContactPointResultDTO(
            contact_point_id=contact_point.id.uuid,
            binding_id=binding.id.uuid,
            contact_point_created=contact_point_created,
            binding_created=True,
            already_attached=False,
        )


__all__ = [
    "AttachContactPointUseCase",
    "AttachContactPointUseCaseProtocol",
]
