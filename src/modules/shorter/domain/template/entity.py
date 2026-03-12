from dataclasses import dataclass
from datetime import datetime

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
        *,
        user_id: EntityIdVO,
        target_module: TemplateTargetModuleTypeVO,
        target_entity: TemplateEntityTypeVO,
        target_entity_id: EntityIdVO,
        default_code: LinkIdVO,
        created_at: datetime,
    ) -> "TemplateEntity":
        return cls(
            id=TemplateIdVO.new(),
            created_at=created_at,
            updated_at=created_at,
            created_by=user_id,
            default_code=default_code,
            target_module=target_module,
            target_entity=target_entity,
            target_entity_id=target_entity_id,
        )
