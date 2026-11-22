from typing import cast
from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.query.preview_field_calculation.query import (
    PreviewFieldCalculationQuery,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationProductNotFoundError,
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    FeedArchivedError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.feed.depends import (
    PreviewFieldCalculationHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.request.preview_field_calculation import (
    PreviewFieldCalculationRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.preview_field_calculation import (
    PreviewFieldCalculationResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def preview_field_calculation(
    feed_id: UUID,
    payload: PreviewFieldCalculationRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PreviewFieldCalculationHandlerDep,
) -> PreviewFieldCalculationResponse:
    """Проверяет права на Feed/выбранную позицию и не принимает исходные цены клиента."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    await require_feed_access(
        context,
        authorization,
        action="feed_builder.feed.calculation_preview",
        feed_id=feed_id,
    )
    principal = context.principal
    assert principal is not None and principal.tenant_id is not None
    for identifier in sorted(
        {
            payload.catalog_item_id,
            payload.catalog_variant_id or payload.catalog_item_id,
        },
        key=str,
    ):
        if not await authorization.can(
            user_id=UUID(principal.user_id),
            tenant_id=UUID(principal.tenant_id),
            action="catalog.item.read",
            resource_type="catalog.item",
            resource_id=identifier,
        ):
            raise HTTPException(
                403,
                {
                    "code": "SOURCE_ACCESS_DENIED",
                    "message": "Недостаточно прав для чтения выбранной позиции Catalog.",
                },
            )
    try:
        result = await handler.execute(
            PreviewFieldCalculationQuery(
                feed_id=FeedIdVO.from_value(feed_id),
                expected_version=payload.expected_version,
                field_id=payload.field_id,
                catalog_item_id=payload.catalog_item_id,
                catalog_variant_id=payload.catalog_variant_id,
                definition_override=(
                    cast(
                        JsonObject,
                        payload.definition_override.model_dump(
                            mode="json", exclude_unset=True
                        ),
                    )
                    if payload.definition_override is not None
                    else None
                ),
            )
        )
    except (FeedNotFoundError, CalculationProductNotFoundError) as exc:
        raise HTTPException(
            404, {"code": "PREVIEW_RESOURCE_NOT_FOUND", "message": str(exc)}
        ) from exc
    except FeedVersionConflictError as exc:
        raise HTTPException(
            409, {"code": "VERSION_CONFLICT", "message": str(exc)}
        ) from exc
    except FeedArchivedError as exc:
        raise HTTPException(
            409, {"code": "FEED_ARCHIVED", "message": str(exc)}
        ) from exc
    except CalculationDependencyUnavailableError as exc:
        raise HTTPException(
            503, {"code": "DEPENDENCY_UNAVAILABLE", "message": str(exc)}
        ) from exc
    except (FeedBuilderDomainError, InvalidFeedSchemaDocumentError) as exc:
        raise HTTPException(
            422,
            {
                "code": (
                    exc.code
                    if isinstance(exc, CalculationDefinitionError)
                    else "SCHEMA_INVALID"
                ),
                "message": str(exc),
                "field_id": str(payload.field_id),
                "path": list(exc.path),
            },
        ) from exc
    return PreviewFieldCalculationResponse.from_dto(result)
