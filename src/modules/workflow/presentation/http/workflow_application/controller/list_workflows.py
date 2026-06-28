from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

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
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.workflow.application.workflow_application import ListWorkflowsQuery
from src.modules.workflow.presentation.depends.application import (
    ListWorkflowsUseCaseDep,
)
from src.modules.workflow.presentation.http.workflow_application.responses import (
    ListWorkflowsResponseSchema,
    WorkflowListItemResponseSchema,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=ListWorkflowsResponseSchema)
async def list_workflows(
    context: AuthenticatedRequestContextDep,
    use_case: ListWorkflowsUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> ListWorkflowsResponseSchema:
    """HTTP endpoint списка workflow applications текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None or not principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListWorkflowsQuery(
                tenant_id=principal.tenant_id,
                limit=limit,
                cursor=cursor,
            )
        )
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
    except (RuntimeDataValidationError, RuntimeDataFilterError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return ListWorkflowsResponseSchema(
        items=[
            WorkflowListItemResponseSchema(
                id=item.id,
                created_at=item.created_at,
                kind=item.kind,
                status=item.status,
                title=item.title,
                description=item.description,
                icon=item.icon,
                icon_background=item.icon_background,
            )
            for item in result.items
        ],
        next_cursor=result.next_cursor,
    )


__all__ = ["router"]
