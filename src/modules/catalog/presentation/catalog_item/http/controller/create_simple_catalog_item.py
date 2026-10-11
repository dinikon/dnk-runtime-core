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
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.create_simple_catalog_item.command import (
    CreateSimpleCatalogItemCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    CreateSimpleCatalogItemHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.create_simple_catalog_item import (
    CreateSimpleCatalogItemResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.create_simple_catalog_item import (
    CreateSimpleCatalogItemRequest,
)


async def create_simple_catalog_item(
    context: AuthenticatedRequestContextDep,
    handler: CreateSimpleCatalogItemHandlerDep,
    payload: CreateSimpleCatalogItemRequest,
) -> CreateSimpleCatalogItemResponse:
    """Преобразует HTTP вход create_simple_catalog_item в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateSimpleCatalogItemCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                virtual=payload.virtual,
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
    return CreateSimpleCatalogItemResponse.model_validate(transport_value(result))
