from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)


async def require_files_admin_context(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует роль tenant admin и отдельное разрешение читать Files Console."""
    return await check_files_admin(context, authorization, "files.read", None)


async def check_files_admin(
    context: RequestContext,
    authorization: AuthorizationServiceProtocol,
    action: str,
    file_id: UUID | None,
) -> RequestContext:
    """Проверяет доверенную роль и отдельное разрешение конкретной файловой операции."""
    principal = context.principal
    if principal is None or not principal.is_authenticated:
        raise HTTPException(401, "Unauthorized.")
    if principal.tenant_id is None or "admin" not in principal.roles:
        raise HTTPException(403, "Tenant administrator is required.")
    allowed = await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action=action,
        resource_type="stored_file",
        resource_id=file_id,
    )
    if not allowed:
        raise HTTPException(403, "Files access is denied.")
    return context


FilesAdminContextDep = Annotated[RequestContext, Depends(require_files_admin_context)]


async def require_files_preview_context(
    file_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует tenant admin и разрешение files.read для конкретного файла."""
    return await check_files_admin(context, authorization, "files.read", file_id)


FilesPreviewContextDep = Annotated[
    RequestContext, Depends(require_files_preview_context)
]


async def require_files_upload_context(
    context: AuthenticatedRequestContextDep, authorization: AuthorizationServiceDep
) -> RequestContext:
    """Требует tenant admin и разрешение files.upload для указанного ресурса."""
    return await check_files_admin(context, authorization, "files.upload", None)


FilesUploadContextDep = Annotated[RequestContext, Depends(require_files_upload_context)]


async def require_files_trash_context(
    file_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует tenant admin и разрешение files.trash для указанного ресурса."""
    return await check_files_admin(context, authorization, "files.trash", file_id)


FilesTrashContextDep = Annotated[RequestContext, Depends(require_files_trash_context)]


async def require_files_restore_context(
    file_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует tenant admin и разрешение files.restore для указанного ресурса."""
    return await check_files_admin(context, authorization, "files.restore", file_id)


FilesRestoreContextDep = Annotated[
    RequestContext, Depends(require_files_restore_context)
]


async def require_files_purge_context(
    file_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует tenant admin и разрешение files.purge для указанного ресурса."""
    return await check_files_admin(context, authorization, "files.purge", file_id)


FilesPurgeContextDep = Annotated[RequestContext, Depends(require_files_purge_context)]


async def require_files_empty_trash_context(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> RequestContext:
    """Требует tenant admin и разрешение files.purge на всю корзину tenant."""
    return await check_files_admin(context, authorization, "files.purge", None)


FilesEmptyTrashContextDep = Annotated[
    RequestContext, Depends(require_files_empty_trash_context)
]
