from dataclasses import asdict
from uuid import UUID
from decimal import Decimal
from src.modules.channels.application.product_representation.command.create_catalog_item_from_publication.command import (
    CreateCatalogItemFromPublicationCommand,
)
from src.modules.channels.presentation.product_representation.depends import (
    CreateCatalogItemFromPublicationHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.product_representation.http.request.create_catalog_item_from_publication import (
    CreateCatalogItemFromPublicationRequest,
)
from src.modules.channels.presentation.product_representation.http.response.create_catalog_item_from_publication import (
    CreateCatalogItemFromPublicationResponse,
)
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)


async def create_catalog_item_from_publication(
    publication_id: UUID,
    context: CatalogCreateContextDep,
    handler: CreateCatalogItemFromPublicationHandlerDep,
    payload: CreateCatalogItemFromPublicationRequest,
) -> CreateCatalogItemFromPublicationResponse:
    """Преобразует HTTP create_catalog_item_from_publication в конкретный use case доверенного tenant."""
    try:
        values = payload.values
        fields = CatalogDraftValuesDTO(
            dict(values.titles),
            values.sku,
            Decimal(values.regular_price) if values.regular_price is not None else None,
            Decimal(values.sale_price) if values.sale_price is not None else None,
            values.currency,
            values.manage_stock,
            Decimal(values.quantity) if values.quantity is not None else None,
            values.stock_status,
            values.backorders,
            dict(values.descriptions),
            tuple(values.gallery),
            values.primary_image_id,
        )
        request = CreateCatalogItemFromPublicationCommand(
            UUID(context.principal.tenant_id),
            UUID(context.principal.user_id),
            publication_id,
            payload.expected_observed_revision,
            payload.request_key,
            fields,
            payload.preparation_id,
            payload.expected_preparation_revision,
        )
        result = await handler.execute(request)
        return CreateCatalogItemFromPublicationResponse(**asdict(result))
    except ChannelsError as error:
        raise http_error(error) from error
