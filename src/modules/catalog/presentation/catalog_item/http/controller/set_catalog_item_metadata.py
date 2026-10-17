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
from src.modules.catalog.application.catalog_item.command.set_catalog_item_metadata.command import (
    SetCatalogItemMetadataCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    SetCatalogItemMetadataHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.set_catalog_item_metadata import (
    SetCatalogItemMetadataResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.set_catalog_item_metadata import (
    SetCatalogItemMetadataRequest,
)


async def set_catalog_item_metadata(
    context: AuthenticatedRequestContextDep,
    handler: SetCatalogItemMetadataHandlerDep,
    item_id: UUID,
    payload: SetCatalogItemMetadataRequest,
) -> SetCatalogItemMetadataResponse:
    """Преобразует HTTP вход set_catalog_item_metadata в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            SetCatalogItemMetadataCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                values=tuple(v.to_entity() for v in payload.metadata),
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
    return SetCatalogItemMetadataResponse.model_validate(transport_value(result))
