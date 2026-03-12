from dataclasses import dataclass

from modules.shorter.domain import TemplateEntity, LinkEntity


@dataclass(frozen=True, slots=True)
class CreateTemplateResult:
    template: TemplateEntity
    link: LinkEntity
