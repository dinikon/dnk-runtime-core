from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.runtime_data.domain.error import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.workflow.application.workflow_application.command import (
    UpdateWorkflowCommand,
)
from src.modules.workflow.domain import WorkflowApplicationNotFoundError
from src.modules.workflow.presentation.depends.application import (
    UpdateWorkflowUseCaseDep,
)
from src.modules.workflow.presentation.http.workflow_application.requests import (
    UpdateWorkflowRequestSchema,
)
from src.modules.workflow.presentation.http.workflow_application.responses import (
    WorkflowResponseSchema,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponseSchema,
)
async def update_workflow(
    workflow_id: UUID,
    payload: UpdateWorkflowRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateWorkflowUseCaseDep,
) -> WorkflowResponseSchema:
    """HTTP endpoint обновления workflow текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None or not principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = UpdateWorkflowCommand(
        tenant_id=principal.tenant_id,
        updated_by=principal.user_id,
        workflow_id=workflow_id,
        title=payload.title,
        description=payload.description,
        icon=payload.icon,
        icon_background=payload.icon_background,
    )

    try:
        result = await use_case(command)
    except WorkflowApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (RuntimeDataValidationError, RuntimeDataFilterError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return WorkflowResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        created_by=result.created_by,
        updated_by=result.updated_by,
        kind=result.kind,
        status=result.status,
        title=result.title,
        description=result.description,
        icon=result.icon,
        icon_background=result.icon_background,
        active_workflow_definition_id=result.active_workflow_definition_id,
    )


__all__ = ["router"]
