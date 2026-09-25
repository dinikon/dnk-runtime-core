from typing import Literal
from fastapi import APIRouter
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.contact_points.presentation.depends.application import (
    ListContactPointLabelsUseCaseDep,
)
from src.modules.contact_points.presentation.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.http.label.responses.schemas import (
    LabelResponse,
)
from src.modules.contact_points.application.label.query.list_labels_query import (
    ListContactPointLabelsQuery,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)

router = APIRouter()


@router.get("", response_model=list[LabelResponse])
async def list_labels(
    context: AuthenticatedRequestContextDep,
    use_case: ListContactPointLabelsUseCaseDep,
    type: Literal["phone", "email"] | None = None,
):
    """Возвращает подписи текущего tenant, включая архивные."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        rows = await use_case(
            ListContactPointLabelsQuery(
                tenant_id, ContactPointType(type) if type else None
            )
        )
        return [LabelResponse.from_dto(row) for row in rows]


__all__ = ["router"]
