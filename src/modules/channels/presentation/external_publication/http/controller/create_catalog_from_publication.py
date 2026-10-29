from uuid import UUID
from fastapi import HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.external_publication.catalog_creation_depends import (
    CreateCatalogFromPublicationHandlerDep,
)
from src.modules.channels.presentation.external_publication.http.response.create_catalog_from_publication import (
    CreateCatalogFromPublicationResponse,
)
from src.modules.channels.application.external_publication.command.create_catalog_from_publication.command import (
    CreateCatalogFromPublicationCommand,
)
from src.modules.channels.application.external_publication.catalog_creation_error import (
    PublicationCatalogError,
)
from src.modules.channels.application.error import (
    VerificationFailure,
    ChannelInputError,
)
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


async def create_catalog_from_publication(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateCatalogFromPublicationHandlerDep,
    channel_id: UUID,
    publication_id: UUID,
    response: Response,
) -> CreateCatalogFromPublicationResponse:
    """Авторизует оба контекста и не раскрывает технические ответы площадок."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    if not await authorization.can(
        user_id=actor_id,
        tenant_id=tenant_id,
        action="catalog.manage",
        resource_type="catalog_item",
    ):
        raise HTTPException(403, detail={"code": "access_denied"})
    try:
        result = await handler.execute(
            CreateCatalogFromPublicationCommand(
                tenant_id, actor_id, channel_id, publication_id
            )
        )
    except PublicationCatalogError as error:
        raise HTTPException(
            (
                404
                if error.code.endswith("_not_found")
                else 409 if error.conflict else 422
            ),
            detail={"code": error.code},
        ) from error
    except VerificationFailure as error:
        raise HTTPException(502, detail={"code": error.code}) from error
    except CatalogBindingError as error:
        raise HTTPException(409, detail={"code": error.code}) from error
    except InvalidExternalPublicationError as error:
        raise HTTPException(
            409, detail={"code": "publication_structure_changed"}
        ) from error
    except (CipherNotConfigured, CiphertextUnreadable, ChannelInputError) as error:
        raise channel_http_error(error) from error
    except ValidationError:
        raise HTTPException(502, detail={"code": "provider_response_invalid"}) from None
    except IntegrityError:
        raise HTTPException(409, detail={"code": "catalog_creation_conflict"}) from None
    response.status_code = 201 if result.created else 200
    return CreateCatalogFromPublicationResponse(
        catalog_item_id=result.catalog_item_id,
        binding_group_id=result.binding_group_id,
        created=result.created,
        warnings=result.warnings,
    )
