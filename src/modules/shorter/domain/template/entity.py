from dataclasses import dataclass
from datetime import datetime

from modules.shared import EntityIdVO
from modules.shorter.domain.link.value_object import LinkIdVO
from modules.shorter.domain.template.value_object import (
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
        code: str,
        target_module: TemplateTargetModuleTypeVO,
        target_entity: TemplateEntityTypeVO,
        target_entity_id: EntityIdVO,
    ):
        now = datetime.now()
        return cls(
            id=TemplateIdVO.new(),
            created_at=now,
            updated_at=now,
            created_by=user_id,
            default_code=LinkIdVO.new(),
            target_module=target_module,
            target_entity=target_entity,
            target_entity_id=target_entity_id,
        )
