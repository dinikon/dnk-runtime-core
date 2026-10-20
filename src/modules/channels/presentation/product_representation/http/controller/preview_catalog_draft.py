from dataclasses import asdict
from uuid import UUID
from fastapi import Query
from src.modules.channels.application.product_representation.query.preview_catalog_draft.query import (
    PreviewCatalogDraftQuery,
)
from src.modules.channels.presentation.product_representation.depends import (
    PreviewCatalogDraftHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.product_representation.http.response.preview_catalog_draft import (
    PreviewCatalogDraftResponse,
    PreviewCatalogDraftValuesResponse,
    PreviewCatalogDraftIssueResponse,
)


async def preview_catalog_draft(
    publication_id: UUID,
    context: CatalogCreateContextDep,
    handler: PreviewCatalogDraftHandlerDep,
    expected_observed_revision: int = Query(ge=1),
    locale: str = Query(min_length=1, max_length=80),
) -> PreviewCatalogDraftResponse:
    """Преобразует HTTP preview_catalog_draft в конкретный use case доверенного tenant."""
    try:
        request = PreviewCatalogDraftQuery(
            UUID(context.principal.tenant_id),
            UUID(context.principal.user_id),
            publication_id,
            expected_observed_revision,
            locale,
        )
        result = await handler.execute(request)
        return PreviewCatalogDraftResponse(
            observed_revision=result.observed_revision,
            values=PreviewCatalogDraftValuesResponse(**asdict(result.values)),
            issues=tuple(
                PreviewCatalogDraftIssueResponse(field=f, message=m)
                for f, m in result.issues
            ),
            warnings=result.warnings,
            main_image_url=result.main_image_url,
            origins=result.origins,
        )
    except ChannelsError as error:
        raise http_error(error) from error
