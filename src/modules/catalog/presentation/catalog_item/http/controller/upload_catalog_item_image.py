from src.modules.catalog.presentation.catalog_item.http.request.upload_catalog_item_image import (
    UploadCatalogItemImageRequest,
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
from src.modules.catalog.presentation.catalog_item.http.serialization import (
    transport_value,
)
from src.modules.catalog.application.catalog_item.command.upload_catalog_item_image.command import (
    UploadCatalogItemImageCommand,
)
from src.modules.catalog.presentation.catalog_item.depends import (
    UploadCatalogItemImageHandlerDep,
)
from src.modules.catalog.presentation.catalog_item.http.response.upload_catalog_item_image import (
    UploadCatalogItemImageResponse,
)
from typing import Annotated
from fastapi import UploadFile, File, Form


async def upload_catalog_item_image(
    context: AuthenticatedRequestContextDep,
    handler: UploadCatalogItemImageHandlerDep,
    item_id: UUID,
    locale: str,
    image: Annotated[UploadFile, File()],
    expected_revision: Annotated[int, Form(ge=1)],
    main: Annotated[bool, Form()] = False,
    alt: Annotated[str, Form(max_length=1000)] = "",
    caption: Annotated[str, Form(max_length=5000)] = "",
) -> UploadCatalogItemImageResponse:
    """Преобразует HTTP вход upload_catalog_item_image в отдельный Application сценарий."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    payload = UploadCatalogItemImageRequest(
        expected_revision=expected_revision,
        main=main,
        alt=alt,
        caption=caption,
    )
    try:
        result = await handler.execute(
            UploadCatalogItemImageCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                item_id=CatalogItemIdVO(item_id),
                expected_revision=expected_revision,
                locale=locale,
                source=image.file,
                size_bytes=image.size or 0,
                name=image.filename or "image",
                content_type=image.content_type or "",
                main=payload.main,
                alt=payload.alt,
                caption=payload.caption,
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
    return UploadCatalogItemImageResponse.model_validate(transport_value(result))
