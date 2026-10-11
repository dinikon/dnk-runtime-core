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
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.replace_catalog_item_gallery.command import (
    ReplaceCatalogItemGalleryCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    ReplaceCatalogItemGalleryHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.replace_catalog_item_gallery import (
    ReplaceCatalogItemGalleryResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.replace_catalog_item_gallery import (
    ReplaceCatalogItemGalleryRequest,
)


async def replace_catalog_item_gallery(
    context: AuthenticatedRequestContextDep,
    handler: ReplaceCatalogItemGalleryHandlerDep,
    item_id: UUID,
    payload: ReplaceCatalogItemGalleryRequest,
    locale: str,
) -> ReplaceCatalogItemGalleryResponse:
    """Преобразует HTTP вход replace_catalog_item_gallery в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ReplaceCatalogItemGalleryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                gallery=payload.gallery.to_entity(),
                expected_root_revision=payload.expected_root_revision,
                locale=locale,
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
    return ReplaceCatalogItemGalleryResponse.model_validate(transport_value(result))
