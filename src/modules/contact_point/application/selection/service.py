from __future__ import annotations

from src.modules.contact_point.application.dto import OwnerContactPointDTO
from src.modules.contact_point.application.selection.command import (
    ContactPointSelectionCommand,
)
from src.modules.contact_point.application.selection.dto import (
    ContactPointSelectionDTO,
    ContactPointSelectionListDTO,
)
from src.modules.contact_point.application.selection.error import (
    ContactPointSelectionNotFoundError,
    ExplicitContactPointNotAttachedError,
    ExplicitContactPointRequiredError,
    ExplicitContactPointTypeMismatchError,
    UnsupportedContactPointChannelError,
    UnsupportedContactPointSelectionStrategyError,
)
from src.modules.contact_point.application.selection.ports import (
    ContactPointSelectionPort,
    ContactPointSelectionRepositoryProtocol,
)
from src.modules.contact_point.application.selection.strategy import (
    ContactPointSelectionStrategy,
)
from src.modules.contact_point.domain.binding import OwnerContactPointBinding
from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


def contact_point_type_for_channel(channel_code: str) -> ContactPointTypeVO:
    normalized_channel = channel_code.strip().upper()
    if normalized_channel in {"SMS", "VIBER"}:
        return ContactPointTypeVO.PHONE
    if normalized_channel == "EMAIL":
        return ContactPointTypeVO.EMAIL
    raise UnsupportedContactPointChannelError(channel_code)


class ContactPointSelectionService(ContactPointSelectionPort):
    def __init__(
        self,
        *,
        repository: ContactPointSelectionRepositoryProtocol,
    ) -> None:
        self._repository = repository

    async def select_one(
        self,
        command: ContactPointSelectionCommand,
    ) -> ContactPointSelectionDTO:
        contact_point_type = contact_point_type_for_channel(command.channel_code)
        owner = OwnerContactPointBinding(
            owner_object_id=command.owner_object_id,
            owner_record_id=command.owner_record_id,
        )

        if command.strategy == ContactPointSelectionStrategy.PRIMARY:
            item = await self._repository.find_active_primary_owner_contact_point(
                tenant_id=command.tenant_id,
                owner=owner,
                contact_point_type=contact_point_type,
            )
            if item is None:
                raise self._not_found(command, contact_point_type)
            return self._to_selection(command, item)

        if command.strategy == ContactPointSelectionStrategy.LAST_ACTIVE:
            item = await self._repository.find_last_active_owner_contact_point(
                tenant_id=command.tenant_id,
                owner=owner,
                contact_point_type=contact_point_type,
            )
            if item is None:
                raise self._not_found(command, contact_point_type)
            return self._to_selection(command, item)

        if command.strategy == ContactPointSelectionStrategy.EXPLICIT_CONTACT_POINT:
            return await self._select_explicit(command, owner, contact_point_type)

        raise UnsupportedContactPointSelectionStrategyError(command.strategy.value)

    async def select_many(
        self,
        command: ContactPointSelectionCommand,
    ) -> ContactPointSelectionListDTO:
        contact_point_type = contact_point_type_for_channel(command.channel_code)
        if command.strategy != ContactPointSelectionStrategy.ALL_ACTIVE:
            raise UnsupportedContactPointSelectionStrategyError(command.strategy.value)

        owner = OwnerContactPointBinding(
            owner_object_id=command.owner_object_id,
            owner_record_id=command.owner_record_id,
        )
        items = await self._repository.list_active_owner_contact_points(
            tenant_id=command.tenant_id,
            owner=owner,
            contact_point_type=contact_point_type,
        )
        if not items:
            raise self._not_found(command, contact_point_type)
        selections = tuple(self._to_selection(command, item) for item in items)
        return ContactPointSelectionListDTO(
            items=selections,
            count=len(selections),
        )

    async def _select_explicit(
        self,
        command: ContactPointSelectionCommand,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> ContactPointSelectionDTO:
        if command.explicit_contact_point_id is None:
            raise ExplicitContactPointRequiredError()
        item = await self._repository.find_active_owner_contact_point(
            tenant_id=command.tenant_id,
            owner=owner,
            contact_point_id=command.explicit_contact_point_id,
        )
        if item is None:
            raise ExplicitContactPointNotAttachedError(
                str(command.explicit_contact_point_id)
            )
        if item.contact_point_type != contact_point_type:
            raise ExplicitContactPointTypeMismatchError(
                contact_point_id=str(command.explicit_contact_point_id),
                expected_type=contact_point_type.value,
                actual_type=item.contact_point_type.value,
            )
        return self._to_selection(command, item)

    def _to_selection(
        self,
        command: ContactPointSelectionCommand,
        item: OwnerContactPointDTO,
    ) -> ContactPointSelectionDTO:
        snapshot = {
            "contact_point_id": str(item.contact_point_id),
            "contact_point_type": item.contact_point_type.value,
            "raw_value": item.raw_value,
            "normalized_value": item.normalized_value,
            "binding_id": str(item.binding_id),
            "owner_object_id": str(command.owner_object_id.uuid),
            "owner_record_id": str(command.owner_record_id.uuid),
            "selection_strategy": command.strategy.value,
            "channel_code": command.channel_code.strip().upper(),
        }
        return ContactPointSelectionDTO(
            contact_point_id=item.contact_point_id,
            contact_point_type=item.contact_point_type,
            recipient_address=item.normalized_value,
            recipient_snapshot=snapshot,
            binding_id=item.binding_id,
            is_primary=item.is_primary,
        )

    def _not_found(
        self,
        command: ContactPointSelectionCommand,
        contact_point_type: ContactPointTypeVO,
    ) -> ContactPointSelectionNotFoundError:
        return ContactPointSelectionNotFoundError(
            owner_object_id=str(command.owner_object_id),
            owner_record_id=str(command.owner_record_id),
            contact_point_type=contact_point_type.value,
            strategy=command.strategy.value,
        )


__all__ = [
    "ContactPointSelectionService",
    "contact_point_type_for_channel",
]
