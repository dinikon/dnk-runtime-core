from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.shorter.application.template.command.create_template import (
    CreateTemplateCommand,
)
from src.modules.shorter.application.template.dto.result_create_template import (
    ResultCreateTemplateDTO,
)
from src.modules.shorter.domain.shared import (
    LinkRepositoryPort,
    TemplateRepositoryPort,
)
from src.modules.shorter.domain.template import TemplateCreationService
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)


class CreateTemplateUseCaseProtocol(Protocol):
    async def execute(
        self,
        command: CreateTemplateCommand,
    ) -> ResultCreateTemplateDTO: ...


class CreateTemplateUseCase:
    def __init__(
        self,
        service: TemplateCreationService,
        template_repository: TemplateRepositoryPort,
        link_repository: LinkRepositoryPort,
    ):
        self._service = service
        self._template_repository = template_repository
        self._link_repository = link_repository

    async def execute(self, command: CreateTemplateCommand) -> ResultCreateTemplateDTO:
        result = await self._service.create(
            created_by=EntityIdVO.from_value(command.created_by),
            domain_id=EntityIdVO.from_value(command.domain_id),
            target_module=TemplateTargetModuleTypeVO(
                command.target_module.strip().lower()
            ),
            target_entity=TemplateEntityTypeVO(command.target_entity.strip().lower()),
            target_entity_id=EntityIdVO.from_value(command.target_entity_id),
            code=command.code,
        )
        await self._template_repository.save(result.template)
        await self._link_repository.save(result.link)
        return ResultCreateTemplateDTO(
            template_id=result.template.id.value,
            link_id=result.link.id.value,
            domain_id=result.link.domain_id.value,
            code=result.link.code,
        )
