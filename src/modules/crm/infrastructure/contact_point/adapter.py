from src.modules.contact_points.application.binding.command.remove_target_contact_points.command import (
    RemoveTargetContactPointsCommand,
)
from src.modules.contact_points.application.binding.command.sync_target_contact_points.command import (
    SyncTargetContactPointsCommand,
)
from src.modules.contact_points.application.binding.query.get_targets_contact_points.query import (
    GetTargetsContactPointsQuery,
)
from src.modules.contact_points.application.binding.query.get_targets_contact_points.handler import (
    GetTargetsContactPointsHandler,
)
from src.modules.contact_points.application.binding.command.remove_target_contact_points.handler import (
    RemoveTargetContactPointsHandler,
)
from src.modules.contact_points.application.binding.command.sync_target_contact_points.handler import (
    SyncTargetContactPointsHandler,
)
from src.modules.contact_points.domain.binding.value_object.draft import (
    ContactPointDraftVO,
)
from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.crm.application.contact_point.dto import (
    ContactPointDTO,
    ContactPointDraftDTO,
    ContactPointsDTO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactPointsAdapter:
    """Переводит CRM-владельца в публичный контракт ContactPoints."""

    def __init__(
        self,
        model_key: str,
        reader: GetTargetsContactPointsHandler,
        writer: SyncTargetContactPointsHandler,
        remover: RemoveTargetContactPointsHandler,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._model_key = model_key
        self._reader = reader
        self._writer = writer
        self._remover = remover
        self._uuid = uuid_generator

    def _target(self, owner_id: EntityIdVO) -> ContactPointTargetVO:
        return ContactPointTargetVO(
            self._model_key, EntityIdVO.from_value(owner_id.uuid)
        )

    async def list(
        self, tenant_id: EntityIdVO, owner_id: EntityIdVO
    ) -> ContactPointsDTO:
        rows = await self._reader.execute(
            GetTargetsContactPointsQuery(tenant_id, (self._target(owner_id),))
        )
        points = tuple(
            ContactPointDTO(
                binding_id=row.binding_id.uuid,
                contact_point_id=row.contact_point_id.uuid,
                type=row.type.value,
                value=row.value,
                country_code=row.country_code,
                label_id=row.label_id.uuid if row.label_id else None,
                position=row.position,
            )
            for row in rows
        )
        return ContactPointsDTO(
            phones=tuple(p for p in points if p.type == ContactPointType.PHONE.value),
            emails=tuple(p for p in points if p.type == ContactPointType.EMAIL.value),
        )

    def _drafts(
        self, drafts: tuple[ContactPointDraftDTO, ...] | None
    ) -> tuple[ContactPointDraftVO, ...] | None:
        if drafts is None:
            return None
        return tuple(
            ContactPointDraftVO(
                candidate_point_id=ContactPointIdVO.from_value(self._uuid.new()),
                candidate_binding_id=ContactPointBindingIdVO.from_value(
                    self._uuid.new()
                ),
                value=draft.value,
                binding_id=(
                    ContactPointBindingIdVO.from_value(draft.binding_id)
                    if draft.binding_id
                    else None
                ),
                label_id=(
                    ContactPointLabelIdVO.from_value(draft.label_id)
                    if draft.label_id
                    else None
                ),
                country_code=draft.country_code,
            )
            for draft in drafts
        )

    async def sync(
        self,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        owner_id: EntityIdVO,
        phones: tuple[ContactPointDraftDTO, ...] | None,
        emails: tuple[ContactPointDraftDTO, ...] | None,
    ) -> None:
        await self._writer.execute(
            SyncTargetContactPointsCommand(
                tenant_id=tenant_id,
                actor_id=actor_id,
                target=self._target(owner_id),
                phones=self._drafts(phones),
                emails=self._drafts(emails),
            )
        )

    async def remove(self, tenant_id: EntityIdVO, owner_id: EntityIdVO) -> None:
        await self._remover.execute(
            RemoveTargetContactPointsCommand(tenant_id, self._target(owner_id))
        )
