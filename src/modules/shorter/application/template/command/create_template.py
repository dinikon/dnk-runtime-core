from dataclasses import dataclass

from modules.shared import EntityIdVO
from modules.shorter.domain import TemplateTargetModuleTypeVO, TemplateEntityTypeVO


@dataclass(frozen=True, slots=True)
class CreateTemplateCommand:
    created_by: EntityIdVO
    domain_id: EntityIdVO
    target_module: TemplateTargetModuleTypeVO
    target_entity: TemplateEntityTypeVO
    target_entity_id: EntityIdVO
    code: str | None = None
