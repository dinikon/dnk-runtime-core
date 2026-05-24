from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.command import DetachContactPointCommand
from src.modules.contact_point.application.dto import DetachContactPointResultDTO
from src.modules.contact_point.domain.binding import (
    ContactPointBindingNotFoundError,
    ContactPointBindingRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class DetachContactPointUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: DetachContactPointCommand,
    ) -> DetachContactPointResultDTO: ...


class DetachContactPointUseCase:
    def __init__(
        self,
        *,
        bindings: ContactPointBindingRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._bindings = bindings
        self._clock = clock

    async def __call__(
        self,
        command: DetachContactPointCommand,
    ) -> DetachContactPointResultDTO:
        binding = await self._bindings.load_binding(
            tenant_id=command.tenant_id,
            binding_id=command.binding_id,
        )
        if binding is None:
            raise ContactPointBindingNotFoundError(str(command.binding_id))

        if not binding.is_active:
            return DetachContactPointResultDTO(
                contact_point_id=binding.contact_point_id.uuid,
                binding_id=binding.id.uuid,
                binding_deleted=False,
                contact_point_deleted=False,
                contact_point_left_orphan=(
                    not await self._bindings.has_active_bindings_for_contact_point(
                        tenant_id=command.tenant_id,
                        contact_point_id=binding.contact_point_id,
                    )
                ),
            )

        now = self._clock.now()
        binding.detach(now=now)
        binding = await self._bindings.save_binding(
            tenant_id=command.tenant_id,
            binding=binding,
        )

        active_primary = await self._bindings.find_active_primary_by_owner_and_type(
            tenant_id=command.tenant_id,
            owner=binding.owner,
            contact_point_type=binding.contact_point_type,
        )
        if active_primary is None:
            promoted = await self._bindings.find_first_active_by_owner_and_type(
                tenant_id=command.tenant_id,
                owner=binding.owner,
                contact_point_type=binding.contact_point_type,
            )
            if promoted is not None:
                promoted.mark_primary(now=now)
                await self._bindings.save_binding(
                    tenant_id=command.tenant_id,
                    binding=promoted,
                )

        contact_point_left_orphan = (
            not await self._bindings.has_active_bindings_for_contact_point(
                tenant_id=command.tenant_id,
                contact_point_id=binding.contact_point_id,
            )
        )
        return DetachContactPointResultDTO(
            contact_point_id=binding.contact_point_id.uuid,
            binding_id=binding.id.uuid,
            binding_deleted=True,
            contact_point_deleted=False,
            contact_point_left_orphan=contact_point_left_orphan,
        )


__all__ = [
    "DetachContactPointUseCase",
    "DetachContactPointUseCaseProtocol",
]
