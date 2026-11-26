from src.modules.feed_builder.application.feed.query.list_field_types.query import (
    ListFieldTypesQuery,
)
from src.modules.feed_builder.presentation.feed.depends import ListFieldTypesHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.list_field_types import (
    ListFieldTypesResponse,
    FieldTypeResponse,
    SchemaLocaleResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_field_types(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListFieldTypesHandlerDep,
) -> ListFieldTypesResponse:
    """Возвращает метаданные после проверки прав, не выдавая значения товаров."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    result = await handler.execute(ListFieldTypesQuery())
    return ListFieldTypesResponse(
        items=tuple(
            FieldTypeResponse(
                kind=item.kind,
                label=item.label,
                supports_locale=item.supports_locale,
                supports_currency=item.supports_currency,
                editable_modes=item.editable_modes,
                type_id=item.type_id,
                type_version=item.type_version,
                forms=item.forms,
            )
            for item in result.items
        ),
        locales=tuple(
            SchemaLocaleResponse(code=item.code, name=item.name)
            for item in result.locales
        ),
        max_fields=result.max_fields,
        max_transforms=result.max_transforms,
    )
