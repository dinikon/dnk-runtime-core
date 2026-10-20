from uuid import UUID
from urllib.parse import urlencode
from dataclasses import asdict
from src.modules.channels.application.publication_import.query.get_publication_import.query import (
    GetPublicationImportQuery,
)
from src.modules.channels.presentation.publication_import.depends import (
    GetPublicationImportHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.publication_import.http.response.get_publication_import import (
    GetPublicationImportResponse,
    PublicationImportImageResponse,
    PublicationImportValuesResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError


async def get_publication_import(
    preparation_id: UUID,
    context: CatalogCreateContextDep,
    handler: GetPublicationImportHandlerDep,
) -> GetPublicationImportResponse:
    """Читает локальный предпросмотр без сетевых вызовов и скрытых мутаций."""
    try:
        result = await handler.execute(
            GetPublicationImportQuery(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                preparation_id,
            )
        )
        values = None
        if result.values is not None:
            raw = asdict(result.values)
            raw.pop("image_files")
            for key in ("regular_price", "sale_price", "quantity"):
                raw[key] = str(raw[key]) if raw[key] is not None else None
            values = PublicationImportValuesResponse(**raw)
        return GetPublicationImportResponse(
            preparation_id=result.preparation_id,
            publication_id=result.publication_id,
            status=result.status,
            revision=result.revision,
            observed_revision=result.observed_revision,
            created_at=result.created_at,
            read_at=result.read_at,
            expires_at=result.expires_at,
            error_code=result.error_code,
            values=values,
            translations=result.translations,
            images=[
                PublicationImportImageResponse(
                    id=image.id,
                    preview_url=(
                        f"/api/console/channels/import-preparations/{preparation_id}/image?"
                        + urlencode({"image_id": image.id})
                        if image.file_id
                        else None
                    ),
                    alt=image.alt,
                    error_code=image.error_code,
                )
                for image in result.images
            ],
            warnings=list(result.warnings),
        )
    except ChannelsError as error:
        raise http_error(error) from error
