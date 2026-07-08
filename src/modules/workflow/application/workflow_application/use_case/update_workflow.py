from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.application.workflow_application.command import (
    UpdateWorkflowCommand,
)
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationDTO,
)
from src.modules.workflow.application.workflow_application.repository import (
    WorkflowApplicationCommandRepositoryProtocol,
)
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowApplicationNotFoundError,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
)


class UpdateWorkflowUseCaseProtocol(Protocol):
    """Use case port for updating workflow application details."""

    async def __call__(self, command: UpdateWorkflowCommand) -> WorkflowApplicationDTO:
        """Updates workflow application details."""
        ...


class UpdateWorkflowUseCase:
    """Updates workflow application details."""

    def __init__(
        self,
        *,
        repository: WorkflowApplicationCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def __call__(self, command: UpdateWorkflowCommand) -> WorkflowApplicationDTO:
        tenant_id = EntityIdVO.from_value(command.tenant_id)
        updated_by = EntityIdVO.from_value(command.updated_by)
        workflow_id = WorkflowApplicationIdVO.from_value(command.workflow_id)

        workflow = await self._repository.load(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
        )
        if workflow is None:
            raise WorkflowApplicationNotFoundError(str(workflow_id.uuid))

        workflow.update_details(
            title=EntityTitleVO(command.title.strip()),
            description=EntityDescriptionVO.optional(
                None if command.description is None else command.description.strip()
            ),
            icon=WorkflowIconVO(command.icon.strip()),
            icon_background=WorkflowIconBackgroundVO(command.icon_background.strip()),
            updated_by=updated_by,
            now=self._clock.now(),
        )
        workflow = await self._repository.save(
            tenant_id=tenant_id,
            workflow=workflow,
        )
        return self._to_dto(workflow)

    @staticmethod
    def _to_dto(workflow: WorkflowApplicationEntity) -> WorkflowApplicationDTO:
        """Maps WorkflowApplicationEntity to WorkflowApplicationDTO."""
        return WorkflowApplicationDTO(
            id=workflow.id.uuid,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=(
                None if workflow.created_by is None else workflow.created_by.uuid
            ),
            updated_by=(
                None if workflow.updated_by is None else workflow.updated_by.uuid
            ),
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
    "UpdateWorkflowUseCase",
    "UpdateWorkflowUseCaseProtocol",
]
