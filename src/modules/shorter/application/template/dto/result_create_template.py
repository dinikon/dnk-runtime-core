from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ResultCreateTemplateDTO:
    template_id: UUID
    link_id: UUID
    domain_id: UUID
    code: str
