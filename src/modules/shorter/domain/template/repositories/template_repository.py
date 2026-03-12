from typing import Protocol

from src.modules.shorter.domain.template.entity import TemplateEntity


class TemplateRepositoryPort(Protocol):
    def save(self, template: TemplateEntity) -> None: ...
