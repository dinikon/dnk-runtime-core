from src.modules.catalog.presentation.catalog_item.stream_depends import (
    ImageStreamsDep,
    close_image_stream,
)
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant_image_content.query import (
    GetCatalogVariantImageContentQuery,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    GetCatalogVariantImageContentHandlerDep,
)
from fastapi.responses import StreamingResponse
from collections.abc import AsyncIterator


async def get_catalog_variant_image_content(
    context: AuthenticatedRequestContextDep,
    handler: GetCatalogVariantImageContentHandlerDep,
    streams: ImageStreamsDep,
    item_id: UUID,
    variant_id: UUID,
    locale: str,
    image_id: UUID,
) -> StreamingResponse:
    """Преобразует HTTP вход get_catalog_variant_image_content в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            GetCatalogVariantImageContentQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                item_id=CatalogItemIdVO(item_id),
                variant_id=CatalogItemIdVO(variant_id),
                locale=locale,
                image_id=image_id,
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(422, "Некорректное значение.") from exc
    except IntegrityError as exc:
        raise HTTPException(
            409, "Конфликт уникального кода или используемой ссылки."
        ) from exc

    streams.push_async_callback(close_image_stream, result.stream)

    async def chunks() -> AsyncIterator[bytes]:
        """Закрывает Files ресурс при завершении и отмене ответа."""
        try:
            async for chunk in result.stream:
                yield chunk
        finally:
            await close_image_stream(result.stream)

    return StreamingResponse(
        chunks(),
        media_type=result.content_type,
        headers={
            "Content-Length": str(result.size_bytes),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
