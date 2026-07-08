from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation import ClockDep, UuidDep
from src.modules.workflow.application.workflow_application import (
    CreateWorkflowUseCase,
    ListWorkflowsUseCase,
    UpdateWorkflowUseCase,
)
from src.modules.workflow.presentation.depends.infrastructure import (
    WorkflowApplicationCommandRepositoryDep,
    WorkflowApplicationQueryRepositoryDep,
    WorkflowDefinitionCommandRepositoryDep,
)


def get_create_workflow_use_case(
    application_repository: WorkflowApplicationCommandRepositoryDep,
    definition_repository: WorkflowDefinitionCommandRepositoryDep,
    clock: ClockDep,
    uuid_generator: UuidDep,
) -> CreateWorkflowUseCase:
    return CreateWorkflowUseCase(
        application_repository=application_repository,
        definition_repository=definition_repository,
        clock=clock,
        uuid_generator=uuid_generator,
    )


CreateWorkflowUseCaseDep = Annotated[
    CreateWorkflowUseCase,
    Depends(get_create_workflow_use_case),
]


def get_list_workflows_use_case(
    repository: WorkflowApplicationQueryRepositoryDep,
) -> ListWorkflowsUseCase:
    return ListWorkflowsUseCase(repository=repository)


ListWorkflowsUseCaseDep = Annotated[
    ListWorkflowsUseCase,
    Depends(get_list_workflows_use_case),
]


def get_update_workflow_use_case(
    repository: WorkflowApplicationCommandRepositoryDep,
    clock: ClockDep,
) -> UpdateWorkflowUseCase:
    return UpdateWorkflowUseCase(
        repository=repository,
        clock=clock,
    )


UpdateWorkflowUseCaseDep = Annotated[
    UpdateWorkflowUseCase,
    Depends(get_update_workflow_use_case),
]


__all__ = [
    "CreateWorkflowUseCaseDep",
    "ListWorkflowsUseCaseDep",
    "UpdateWorkflowUseCaseDep",
    "get_create_workflow_use_case",
    "get_list_workflows_use_case",
    "get_update_workflow_use_case",
]
