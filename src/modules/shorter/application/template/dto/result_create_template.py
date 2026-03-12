from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ResultCreateTemplateDTO:
    id: UUID
    template_name: str
    description: str
