from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation import ClockDep, UuidDep
from src.modules.workflow.application.workflow_application import CreateWorkflowUseCase
from src.modules.workflow.presentation.depends.infrastructure import (
    WorkflowApplicationCommandRepositoryDep,
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


__all__ = [
    "CreateWorkflowUseCaseDep",
    "get_create_workflow_use_case",
]
