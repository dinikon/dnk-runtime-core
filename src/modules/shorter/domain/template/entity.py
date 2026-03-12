from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.shared import EntityIdVO
from ..link.value_object import LinkIdVO
from .value_object import (
    TemplateIdVO,
    TemplateTargetModuleTypeVO,
    TemplateEntityTypeVO,
)


@dataclass(slots=True)
class TemplateEntity:
    id: TemplateIdVO

    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO

    default_code: LinkIdVO

    target_module: TemplateTargetModuleTypeVO
    target_entity: TemplateEntityTypeVO
    target_entity_id: EntityIdVO

    @classmethod
    def create(
        cls,
        user_id: EntityIdVO,
        target_module: TemplateTargetModuleTypeVO,
        target_entity: TemplateEntityTypeVO,
        target_entity_id: EntityIdVO,
        default_code: LinkIdVO | None = None,
        created_at: datetime | None = None,
    ) -> "TemplateEntity":
        now = created_at or datetime.now(UTC)
        return cls(
            id=TemplateIdVO.new(),
            created_at=now,
            updated_at=now,
            created_by=user_id,
            default_code=default_code or LinkIdVO.new(),
            target_module=target_module,
            target_entity=target_entity,
            target_entity_id=target_entity_id,
        )
