from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateTemplateCommand:
    created_by: UUID
    domain_id: UUID
    target_module: str
    target_entity: str
    target_entity_id: UUID
    code: str | None
