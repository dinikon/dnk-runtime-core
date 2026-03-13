from typing import Protocol

from src.modules.shorter.domain.template.entity import TemplateEntity
from src.modules.shorter.domain.template.value_object import TemplateIdVO


class TemplateRepositoryPort(Protocol):
    async def save(self, template: TemplateEntity) -> None: ...

    async def get_by_id(
        self,
        *,
        template_id: TemplateIdVO,
    ) -> TemplateEntity | None: ...
