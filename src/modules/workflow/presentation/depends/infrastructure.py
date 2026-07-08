from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.presentation.depends.application import (
    RuntimeObjectResolverDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.workflow.application.workflow_application.repository import (
    WorkflowApplicationCommandRepositoryProtocol,
    WorkflowApplicationQueryRepositoryProtocol,
)
from src.modules.workflow.application.workflow_definition.repository import (
    WorkflowDefinitionCommandRepositoryProtocol,
)
from src.modules.workflow.infrastructure import (
    WorkflowApplicationRuntimeRepository,
    WorkflowDefinitionRuntimeRepository,
)


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_query_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeQueryGateway:
    return PostgresRuntimeQueryGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeQueryGatewayDep = Annotated[
    PostgresRuntimeQueryGateway,
    Depends(get_runtime_query_gateway),
]


def get_runtime_command_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> PostgresRuntimeCommandGateway:
    return PostgresRuntimeCommandGateway(
        uow.session,
        type_policy=type_policy,
        query_gateway=runtime_query_gateway,
    )


RuntimeCommandGatewayDep = Annotated[
    PostgresRuntimeCommandGateway,
    Depends(get_runtime_command_gateway),
]


def get_workflow_application_runtime_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> WorkflowApplicationRuntimeRepository:
    return WorkflowApplicationRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


WorkflowApplicationRuntimeRepositoryDep = Annotated[
    WorkflowApplicationRuntimeRepository,
    Depends(get_workflow_application_runtime_repository),
]


def get_workflow_definition_runtime_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> WorkflowDefinitionRuntimeRepository:
    return WorkflowDefinitionRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


WorkflowDefinitionRuntimeRepositoryDep = Annotated[
    WorkflowDefinitionRuntimeRepository,
    Depends(get_workflow_definition_runtime_repository),
]


def get_workflow_application_command_repository(
    repository: WorkflowApplicationRuntimeRepositoryDep,
) -> WorkflowApplicationCommandRepositoryProtocol:
    return repository


def get_workflow_application_query_repository(
    repository: WorkflowApplicationRuntimeRepositoryDep,
) -> WorkflowApplicationQueryRepositoryProtocol:
    return repository


def get_workflow_definition_command_repository(
    repository: WorkflowDefinitionRuntimeRepositoryDep,
) -> WorkflowDefinitionCommandRepositoryProtocol:
    return repository


WorkflowApplicationCommandRepositoryDep = Annotated[
    WorkflowApplicationCommandRepositoryProtocol,
    Depends(get_workflow_application_command_repository),
]

WorkflowApplicationQueryRepositoryDep = Annotated[
    WorkflowApplicationQueryRepositoryProtocol,
    Depends(get_workflow_application_query_repository),
]

WorkflowDefinitionCommandRepositoryDep = Annotated[
    WorkflowDefinitionCommandRepositoryProtocol,
    Depends(get_workflow_definition_command_repository),
]


__all__ = [
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "WorkflowApplicationCommandRepositoryDep",
    "WorkflowApplicationQueryRepositoryDep",
    "WorkflowApplicationRuntimeRepositoryDep",
    "WorkflowDefinitionCommandRepositoryDep",
    "WorkflowDefinitionRuntimeRepositoryDep",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
    "get_workflow_application_command_repository",
    "get_workflow_application_query_repository",
    "get_workflow_application_runtime_repository",
    "get_workflow_definition_command_repository",
    "get_workflow_definition_runtime_repository",
]
