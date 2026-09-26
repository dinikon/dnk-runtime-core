from src.modules.crm.application.contact_points.port import (
    ContactPointDTO,
    ContactPointsDTO,
)
from src.modules.crm.domain.error import InvalidCrmContactPointError
from src.modules.contact_points.application.api import (
    SyncTargetContactPointsCommand,
    RemoveTargetContactPointsCommand,
    GetTargetsContactPointsQuery,
    SyncTargetContactPointsUseCase,
    GetTargetsContactPointsUseCase,
    RemoveTargetContactPointsUseCase,
)
from src.modules.contact_points.domain.api import (
    ContactPointBindingIdVO,
    ContactPointTargetVO,
    ContactPointDraftVO,
    InvalidContactPointBindingError,
    ContactPointIdVO,
    ContactPointLabelIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def _drafts(items):
    if items is None:
        return None
    return tuple(
        ContactPointDraftVO(
            candidate_point_id=ContactPointIdVO.from_value(item.candidate_point_id),
            candidate_binding_id=ContactPointBindingIdVO.from_value(
                item.candidate_binding_id
            ),
            value=item.value,
            binding_id=(
                ContactPointBindingIdVO.from_value(item.binding_id)
                if item.binding_id
                else None
            ),
            label_id=(
                ContactPointLabelIdVO.from_value(item.label_id)
                if item.label_id
                else None
            ),
            country_code=item.country_code,
        )
        for item in items
    )


class ContactPointsApplicationAdapter:
    """Переводит контракт CRM в публичные операции contact_points без HTTP и commit."""

    def __init__(
        self,
        sync: SyncTargetContactPointsUseCase,
        read: GetTargetsContactPointsUseCase,
        remove: RemoveTargetContactPointsUseCase,
    ):
        self.sync_use_case, self.read_use_case, self.remove_use_case = (
            sync,
            read,
            remove,
        )

    async def sync(self, tenant_id, actor_id, model_key, record_id, phones, emails):
        """Сохраняет списки на UoW, уже открытой для CRM."""
        try:
            await self.sync_use_case(
                SyncTargetContactPointsCommand(
                    tenant_id,
                    actor_id,
                    ContactPointTargetVO(model_key, record_id),
                    _drafts(phones),
                    _drafts(emails),
                )
            )
        except InvalidContactPointBindingError as exc:
            raise InvalidCrmContactPointError(
                str(exc), exc.array, exc.index, exc.field
            ) from exc

    async def get_many(self, tenant_id, model_key, record_ids):
        """Читает адреса страницы и возвращает только CRM DTO."""
        targets = tuple(
            ContactPointTargetVO(model_key, record_id) for record_id in record_ids
        )
        rows = await self.read_use_case(
            GetTargetsContactPointsQuery(tenant_id, targets)
        )
        values = {record_id: {"phone": [], "email": []} for record_id in record_ids}
        for row in rows:
            values[row.target.record_id][row.type.value].append(
                ContactPointDTO(
                    binding_id=EntityIdVO.from_value(row.binding_id.uuid),
                    contact_point_id=EntityIdVO.from_value(row.contact_point_id.uuid),
                    value=row.value,
                    label_id=(
                        EntityIdVO.from_value(row.label_id.uuid)
                        if row.label_id
                        else None
                    ),
                    country_code=row.country_code,
                )
            )
        return {
            record_id: ContactPointsDTO(tuple(groups["phone"]), tuple(groups["email"]))
            for record_id, groups in values.items()
        }

    async def remove(self, tenant_id, model_key, record_id):
        """Удаляет связи перед удалением заблокированного CRM-объекта."""
        await self.remove_use_case(
            RemoveTargetContactPointsCommand(
                tenant_id, ContactPointTargetVO(model_key, record_id)
            )
        )


__all__ = ["ContactPointsApplicationAdapter"]
