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
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.change_catalog_item_kind.command import (
    ChangeCatalogItemKindCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    ChangeCatalogItemKindHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.change_catalog_item_kind import (
    ChangeCatalogItemKindResponse,
)
from src.modules.catalog.presentation.catalog_item.http.request.change_catalog_item_kind import (
    ChangeCatalogItemKindRequest,
)


async def change_catalog_item_kind(
    context: AuthenticatedRequestContextDep,
    handler: ChangeCatalogItemKindHandlerDep,
    item_id: UUID,
    payload: ChangeCatalogItemKindRequest,
) -> ChangeCatalogItemKindResponse:
    """Преобразует HTTP вход change_catalog_item_kind в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            ChangeCatalogItemKindCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                kind=CatalogItemKind(payload.kind),
                structure=payload.structure.to_input() if payload.structure else None,
                selected_item_id=(
                    CatalogItemIdVO(payload.selected_item_id)
                    if payload.selected_item_id
                    else None
                ),
                discarded_ids=frozenset(
                    CatalogItemIdVO(i) for i in payload.discarded_ids
                ),
                carry_to_index=payload.carry_to_index,
                expected_root_revision=payload.expected_root_revision,
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
    return ChangeCatalogItemKindResponse.model_validate(transport_value(result))
