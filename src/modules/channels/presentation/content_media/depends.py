from src.modules.channels.presentation.content_media.assembly import (
    ContentMediaRuntime,
    build_content_media_runtime,
)
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from src.modules.channels.application.content_media.query.get_media_content.handler import (
    GetMediaContentHandler,
)
from src.modules.channels.application.content_media.command.prepare_gallery.handler import (
    PrepareGalleryHandler,
)
from src.modules.channels.application.content_media.command.revoke_media_access.handler import (
    RevokeMediaAccessHandler,
)
from src.modules.channels.application.content_media.command.renew_media_access.handler import (
    RenewMediaAccessHandler,
)
from src.modules.channels.infrastructure.content_media.authorization import (
    MediaFilesAuthorization,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.depends import (
    get_platforms,
    tenant_id_from_context,
)
from src.modules.files.infrastructure.assembly import get_storage_resolver
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.crypto.depends import CipherDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.shared.presentation.http.host import extract_request_host
from src.modules.tenancy.presentation.depends.application import (
    TenantRequestContextByHostUseCaseDep,
)
from src.modules.tenancy.application.tenant_domain.query.resolve_tenant_request_context_by_host_query import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.domain.tenant_domain.error import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


@dataclass(frozen=True, slots=True)
class MediaTenant:
    """Канонический tenant и API origin, полученные из зарегистрированного домена."""

    id: UUID
    base_url: str


async def get_media_tenant(
    request: Request, tenants: TenantRequestContextByHostUseCaseDep
) -> MediaTenant:
    """Не использует cookies, tenant ID из URL или произвольный Host для выдачи ссылки."""
    try:
        tenant = await tenants.execute(
            ResolveTenantRequestContextByHostQuery(extract_request_host(request))
        )
    except (TenantHostNotFoundError, TenantLoginUnavailableError):
        raise HTTPException(404, detail={"code": "media_not_found"}) from None
    if getattr(request.state, "tenant_connection", None) is None:
        raise HTTPException(404, detail={"code": "media_not_found"})
    return MediaTenant(tenant.tenant_id, "https://" + (tenant.api_host or tenant.host))


MediaTenantDep = Annotated[MediaTenant, Depends(get_media_tenant)]


def get_content_media_runtime(
    tenant: MediaTenantDep,
    uow: UoWDep,
    cipher: CipherDep,
    clock: ClockDep,
    uuid: UuidDep,
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> ContentMediaRuntime:
    """Подключает контекст HTTP к той же сборке, что используется исполнителем."""
    return build_content_media_runtime(
        session=uow.session,
        tenant_id=tenant.id,
        base_url=tenant.base_url,
        uow=uow,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
        storage=get_storage_resolver(),
    )


ContentMediaRuntimeDep = Annotated[
    ContentMediaRuntime, Depends(get_content_media_runtime)
]


def get_media_authorization(
    tenant: MediaTenantDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> MediaFilesAuthorization:
    """Проверяет совпадение домена и authenticated tenant до выдачи URL."""
    if tenant_id_from_context(context) != tenant.id:
        raise HTTPException(403, detail={"code": "access_denied"})
    assert context.principal is not None
    return MediaFilesAuthorization(
        tenant_id=tenant.id,
        actor_id=UUID(context.principal.user_id),
        authorization=authorization,
    )


MediaAuthorizationDep = Annotated[
    MediaFilesAuthorization, Depends(get_media_authorization)
]


def get_prepare_gallery_handler(
    runtime: ContentMediaRuntimeDep, authorization: MediaAuthorizationDep
) -> PrepareGalleryHandler:
    """Собирает явную подготовку галерей."""
    return PrepareGalleryHandler(runtime.galleries, authorization)


PrepareGalleryHandlerDep = Annotated[
    PrepareGalleryHandler, Depends(get_prepare_gallery_handler)
]


def get_media_content_handler(
    runtime: ContentMediaRuntimeDep,
) -> GetMediaContentHandler:
    """Собирает ограниченное чтение без authenticated dependency."""
    return GetMediaContentHandler(runtime.galleries)


GetMediaContentHandlerDep = Annotated[
    GetMediaContentHandler, Depends(get_media_content_handler)
]


def get_revoke_media_access_handler(
    runtime: ContentMediaRuntimeDep, authorization: MediaAuthorizationDep
) -> RevokeMediaAccessHandler:
    """Собирает отзыв только для текущего tenant."""
    return RevokeMediaAccessHandler(runtime.transfers)


RevokeMediaAccessHandlerDep = Annotated[
    RevokeMediaAccessHandler, Depends(get_revoke_media_access_handler)
]


def get_renew_media_access_handler(
    runtime: ContentMediaRuntimeDep, authorization: MediaAuthorizationDep
) -> RenewMediaAccessHandler:
    """Собирает ротацию с повторной проверкой права Files."""
    return RenewMediaAccessHandler(runtime.transfers, authorization)


RenewMediaAccessHandlerDep = Annotated[
    RenewMediaAccessHandler, Depends(get_renew_media_access_handler)
]
