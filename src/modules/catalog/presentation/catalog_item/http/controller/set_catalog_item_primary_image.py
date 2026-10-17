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
from src.modules.catalog.application.catalog_item.command.set_catalog_item_primary_image.command import (
    SetCatalogItemPrimaryImageCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemPrimaryImageHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_primary_image import (
    SetCatalogItemPrimaryImageResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_primary_image import (
    SetCatalogItemPrimaryImageRequest,
)


async def set_catalog_item_primary_image(
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemPrimaryImageHandlerDep,
    item_id: UUID,
    payload: SetCatalogItemPrimaryImageRequest,
    locale: str,
) -> SetCatalogItemPrimaryImageResponse:
    """Преобразует HTTP вход set_catalog_item_primary_image в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetCatalogItemPrimaryImageCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                image_id=payload.image_id,
                expected_revision=payload.expected_revision,
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
    return SetCatalogItemPrimaryImageResponse.model_validate(transport_value(result))
