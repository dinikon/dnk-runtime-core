from uuid import UUID
from fastapi import HTTPException, Query, Response
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
from src.modules.catalog.application.catalog_item.command.delete_catalog_item_gallery.command import (
    DeleteCatalogItemGalleryCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    DeleteCatalogItemGalleryHandlerDep,
)


async def delete_catalog_item_gallery(
    context: AuthenticatedRequestContextDep,
    handler: DeleteCatalogItemGalleryHandlerDep,
    item_id: UUID,
    locale: str,
    expected_revision: int = Query(ge=1),
) -> Response:
    """Преобразует HTTP вход delete_catalog_item_gallery в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            DeleteCatalogItemGalleryCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                expected_revision=expected_revision,
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
    return Response(status_code=204)
