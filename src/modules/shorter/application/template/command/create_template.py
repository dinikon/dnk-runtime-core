from dataclasses import dataclass

from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)


@dataclass(frozen=True, slots=True)
class CreateTemplateCommand:
    created_by: EntityIdVO
    domain_id: EntityIdVO
    target_module: TemplateTargetModuleTypeVO
    target_entity: TemplateEntityTypeVO
    target_entity_id: EntityIdVO
    code: str | None = None
