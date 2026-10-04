from typing import Literal

from src.modules.contact_points.application.label.query.list_labels.query import (
    ListContactPointLabelsQuery,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.presentation.label.depends import (
    ListContactPointLabelsHandlerDep,
)
from src.modules.contact_points.presentation.label.http.boundary import (
    context_ids,
    http_errors,
)
from src.modules.contact_points.presentation.label.http.response.list_labels import (
    ListLabelResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_labels(
    context: AuthenticatedRequestContextDep,
    handler: ListContactPointLabelsHandlerDep,
    type: Literal["phone", "email"] | None = None,
) -> list[ListLabelResponse]:
    """Возвращает подписи текущего tenant, включая архивные."""
    with http_errors():
        tenant_id, _ = context_ids(context)
        rows = await handler.execute(
            ListContactPointLabelsQuery(
                tenant_id, ContactPointType(type) if type else None
            )
        )
        return [ListLabelResponse.from_dto(row) for row in rows]
