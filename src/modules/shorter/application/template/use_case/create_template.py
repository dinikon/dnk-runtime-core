from typing import Protocol

from src.modules.shorter.application.template.command.create_template import (
    CreateTemplateCommand,
)
from src.modules.shorter.application.template.dto.result_create_template import (
    ResultCreateTemplateDTO,
)
from src.modules.shorter.domain.template.service import TemplateCreateService


class CreateTemplateUseCaseProtocol(Protocol):
    def execute(self, command: CreateTemplateCommand) -> ResultCreateTemplateDTO: ...


class CreateTemplateUseCase:
    def __init__(self, service: TemplateCreateService):
        self._service = service

    def execute(self, command: CreateTemplateCommand) -> ResultCreateTemplateDTO:
        result = self._service.create(
            created_by=command.created_by,
            domain_id=command.domain_id,
            target_module=command.target_module,
            target_entity=command.target_entity,
            target_entity_id=command.target_entity_id,
            code=command.code,
        )
        return ResultCreateTemplateDTO(
            template_id=result.template.id.value,
            link_id=result.link.id.value,
            domain_id=result.link.domain_id.value,
            code=result.link.code,
        )
