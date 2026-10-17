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
from src.modules.catalog.application.catalog_item.command.put_catalog_item_content.command import (
    PutCatalogItemContentCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    PutCatalogItemContentHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.put_catalog_item_content import (
    PutCatalogItemContentResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.put_catalog_item_content import (
    PutCatalogItemContentRequest,
)


async def put_catalog_item_content(
    context: AuthenticatedRequestContextDep,
    handler: PutCatalogItemContentHandlerDep,
    item_id: UUID,
    payload: PutCatalogItemContentRequest,
    locale: str,
) -> PutCatalogItemContentResponse:
    """Преобразует HTTP вход put_catalog_item_content в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            PutCatalogItemContentCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                expected_schema_version=payload.expected_schema_version,
                values=payload.values,
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
    return PutCatalogItemContentResponse.model_validate(transport_value(result))
