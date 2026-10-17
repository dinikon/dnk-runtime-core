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
from src.modules.catalog.application.catalog_item.command.set_catalog_item_tags.command import (
    SetCatalogItemTagsCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemTagsHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_tags import (
    SetCatalogItemTagsResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_tags import (
    SetCatalogItemTagsRequest,
)


async def set_catalog_item_tags(
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemTagsHandlerDep,
    item_id: UUID,
    payload: SetCatalogItemTagsRequest,
) -> SetCatalogItemTagsResponse:
    """Преобразует HTTP вход set_catalog_item_tags в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetCatalogItemTagsCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                tag_ids=payload.tag_ids,
                expected_revision=payload.expected_revision,
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
    return SetCatalogItemTagsResponse.model_validate(transport_value(result))
