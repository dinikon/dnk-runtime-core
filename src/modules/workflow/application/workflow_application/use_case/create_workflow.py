from typing import Protocol

from src.modules.shared import EntityIdVO, UUIdGeneratorProtocol
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.application.workflow_application.command import (
    CreateWorkflowCommand,
)
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationDTO,
)
from src.modules.workflow.application.workflow_application.repository import (
    WorkflowApplicationCommandRepositoryProtocol,
)
from src.modules.workflow.application.workflow_definition import (
    WorkflowDefinitionCommandRepositoryProtocol,
)
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowDefinitionEntity,
    WorkflowDefinitionIdVO,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
)


class CreateWorkflowUseCaseProtocol(Protocol):
    """Use case port for creating a default workflow."""

    async def __call__(self, command: CreateWorkflowCommand) -> WorkflowApplicationDTO:
        """Creates a workflow application with an initial draft definition."""
        ...


class CreateWorkflowUseCase:
    """Creates a default workflow application and its initial draft definition."""

    def __init__(
        self,
        *,
        application_repository: WorkflowApplicationCommandRepositoryProtocol,
        definition_repository: WorkflowDefinitionCommandRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._application_repository = application_repository
        self._definition_repository = definition_repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def __call__(self, command: CreateWorkflowCommand) -> WorkflowApplicationDTO:
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        created_by = EntityIdVO.from_value(command.created_by)
        workflow_id = WorkflowApplicationIdVO.from_value(self._uuid_generator.new())
        definition_id = WorkflowDefinitionIdVO.from_value(self._uuid_generator.new())
        now = self._clock.now()

        title = EntityTitleVO(command.title.strip())
        description = EntityDescriptionVO.optional(command.description)

        workflow = WorkflowApplicationEntity.create(
            entity_id=workflow_id,
            kind=WorkflowKindVO.STANDARD,
            title=title,
            description=description,
            icon=WorkflowIconVO(command.icon.strip()),
            icon_background=WorkflowIconBackgroundVO(
                command.icon_background.strip()
            ),
            created_by=created_by,
            now=now,
        )
        definition = WorkflowDefinitionEntity.create_draft(
            workflow_definition_id=definition_id,
            workflow_application_id=workflow.id,
            graph=WorkflowGraphVO({}),
            features=WorkflowFeaturesVO({}),
            environment=WorkflowEnvironmentVO([]),
            title=title,
            description=description,
            created_by=created_by,
            now=now,
        )

        workflow = await self._application_repository.save(
            tenant_id=tenant_id,
            workflow=workflow,
        )
        await self._definition_repository.save(
            tenant_id=tenant_id,
            definition=definition,
        )
        return self._to_dto(workflow)

    @staticmethod
    def _to_dto(workflow: WorkflowApplicationEntity) -> WorkflowApplicationDTO:
        """Maps WorkflowApplicationEntity to WorkflowApplicationDTO."""
        return WorkflowApplicationDTO(
            id=workflow.id.uuid,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=None if workflow.created_by is None else workflow.created_by.uuid,
            updated_by=None if workflow.updated_by is None else workflow.updated_by.uuid,
            kind=workflow.kind.value,
            status=workflow.status.value,
            title=workflow.title.value,
            description=(
                None if workflow.description is None else workflow.description.value
            ),
            icon=workflow.icon.value,
            icon_background=workflow.icon_background.value,
            active_workflow_definition_id=(
                None
                if workflow.active_workflow_definition_id is None
                else workflow.active_workflow_definition_id.uuid
            ),
        )


__all__ = [
    "CreateWorkflowUseCase",
    "CreateWorkflowUseCaseProtocol",
]
