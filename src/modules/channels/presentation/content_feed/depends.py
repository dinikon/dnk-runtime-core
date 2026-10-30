from typing import Annotated

from fastapi import Depends, HTTPException

from src.modules.channels.presentation.content_feed.assembly import (
    ContentFeedRuntime,
    build_content_feed_runtime,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)
from src.modules.channels.presentation.content_media.depends import MediaTenantDep
from src.modules.channels.presentation.depends import (
    get_platforms,
    tenant_id_from_context,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.files.infrastructure.assembly import get_storage_resolver
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.crypto.depends import CipherDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.channels.application.content_feed.command.create_content_feed.handler import (
    CreateContentFeedHandler,
)
from src.modules.channels.application.content_feed.command.change_content_feed_source.handler import (
    ChangeContentFeedSourceHandler,
)
from src.modules.channels.application.content_feed.command.enable_content_feed.handler import (
    EnableContentFeedHandler,
)
from src.modules.channels.application.content_feed.command.disable_content_feed.handler import (
    DisableContentFeedHandler,
)
from src.modules.channels.application.content_feed.command.rotate_feed_access.handler import (
    RotateFeedAccessHandler,
)
from src.modules.channels.application.content_feed.command.revoke_feed_access.handler import (
    RevokeFeedAccessHandler,
)
from src.modules.channels.application.content_feed.query.get_content_feed.handler import (
    GetContentFeedHandler,
)
from src.modules.channels.application.content_feed.query.list_content_feeds.handler import (
    ListContentFeedsHandler,
)
from src.modules.channels.application.content_feed.query.preview_content_feed.handler import (
    PreviewContentFeedHandler,
)
from src.modules.channels.application.content_feed.command.delete_content_feed.handler import (
    DeleteContentFeedHandler,
)
from src.modules.channels.application.content_feed.query.get_content_feed_xml.handler import (
    GetContentFeedXmlHandler,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports
from src.modules.channels.application.content_feed.command.request_feed_import.handler import (
    RequestFeedImportHandler,
)
from src.modules.channels.application.content_feed.command.resume_feed_import.handler import (
    ResumeFeedImportHandler,
)
from src.modules.channels.application.content_feed.command.attach_feed_import.handler import (
    AttachFeedImportHandler,
)
from src.modules.channels.application.content_feed.command.resolve_feed_import.handler import (
    ResolveFeedImportHandler,
)
from src.modules.channels.application.content_feed.query.get_feed_import.handler import (
    GetFeedImportHandler,
)


def get_content_feed_runtime(
    tenant: MediaTenantDep,
    authorization: AuthorizationServiceDep,
    uow: UoWDep,
    cipher: CipherDep,
    clock: ClockDep,
    uuid: UuidDep,
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> ContentFeedRuntime:
    """Собирает публичный и Console-пути на одном каноническом tenant-соединении."""
    return build_content_feed_runtime(
        session=uow.session,
        tenant_id=tenant.id,
        base_url=tenant.base_url,
        uow=uow,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
        storage=get_storage_resolver(),
        authorization=authorization,
    )


ContentFeedRuntimeDep = Annotated[ContentFeedRuntime, Depends(get_content_feed_runtime)]


def get_feed_management(
    runtime: ContentFeedRuntimeDep,
    tenant: MediaTenantDep,
    context: AuthenticatedRequestContextDep,
) -> ContentFeedManagement:
    """Не допускает управление ресурсом домена из другого authenticated tenant."""
    if tenant_id_from_context(context) != tenant.id:
        raise HTTPException(403, detail={"code": "access_denied"})
    return runtime.management


FeedManagementDep = Annotated[ContentFeedManagement, Depends(get_feed_management)]


def get_create_content_feed_handler(
    management: FeedManagementDep,
) -> CreateContentFeedHandler:
    """Собирает отдельный сценарий create_content_feed на общем UoW."""
    return CreateContentFeedHandler(management)


CreateContentFeedHandlerDep = Annotated[
    CreateContentFeedHandler, Depends(get_create_content_feed_handler)
]


def get_change_content_feed_source_handler(
    management: FeedManagementDep,
) -> ChangeContentFeedSourceHandler:
    """Собирает отдельный сценарий change_content_feed_source на общем UoW."""
    return ChangeContentFeedSourceHandler(management)


ChangeContentFeedSourceHandlerDep = Annotated[
    ChangeContentFeedSourceHandler, Depends(get_change_content_feed_source_handler)
]


def get_enable_content_feed_handler(
    management: FeedManagementDep,
) -> EnableContentFeedHandler:
    """Собирает отдельный сценарий enable_content_feed на общем UoW."""
    return EnableContentFeedHandler(management)


EnableContentFeedHandlerDep = Annotated[
    EnableContentFeedHandler, Depends(get_enable_content_feed_handler)
]


def get_disable_content_feed_handler(
    management: FeedManagementDep,
) -> DisableContentFeedHandler:
    """Собирает отдельный сценарий disable_content_feed на общем UoW."""
    return DisableContentFeedHandler(management)


DisableContentFeedHandlerDep = Annotated[
    DisableContentFeedHandler, Depends(get_disable_content_feed_handler)
]


def get_rotate_feed_access_handler(
    management: FeedManagementDep,
) -> RotateFeedAccessHandler:
    """Собирает отдельный сценарий rotate_feed_access на общем UoW."""
    return RotateFeedAccessHandler(management)


RotateFeedAccessHandlerDep = Annotated[
    RotateFeedAccessHandler, Depends(get_rotate_feed_access_handler)
]


def get_revoke_feed_access_handler(
    management: FeedManagementDep,
) -> RevokeFeedAccessHandler:
    """Собирает отдельный сценарий revoke_feed_access на общем UoW."""
    return RevokeFeedAccessHandler(management)


RevokeFeedAccessHandlerDep = Annotated[
    RevokeFeedAccessHandler, Depends(get_revoke_feed_access_handler)
]


def get_get_content_feed_handler(
    management: FeedManagementDep,
) -> GetContentFeedHandler:
    """Собирает отдельный сценарий get_content_feed на общем UoW."""
    return GetContentFeedHandler(management)


GetContentFeedHandlerDep = Annotated[
    GetContentFeedHandler, Depends(get_get_content_feed_handler)
]


def get_list_content_feeds_handler(
    management: FeedManagementDep,
) -> ListContentFeedsHandler:
    """Собирает отдельный сценарий list_content_feeds на общем UoW."""
    return ListContentFeedsHandler(management)


ListContentFeedsHandlerDep = Annotated[
    ListContentFeedsHandler, Depends(get_list_content_feeds_handler)
]


def get_preview_content_feed_handler(
    management: FeedManagementDep, uow: UoWDep
) -> PreviewContentFeedHandler:
    """Собирает отдельный сценарий preview_content_feed на общем UoW."""
    return PreviewContentFeedHandler(management, uow)


PreviewContentFeedHandlerDep = Annotated[
    PreviewContentFeedHandler, Depends(get_preview_content_feed_handler)
]


def get_delete_content_feed_handler(
    management: FeedManagementDep,
) -> DeleteContentFeedHandler:
    """Собирает отдельный сценарий delete_content_feed на общем UoW."""
    return DeleteContentFeedHandler(management)


DeleteContentFeedHandlerDep = Annotated[
    DeleteContentFeedHandler, Depends(get_delete_content_feed_handler)
]


def get_content_feed_xml_handler(
    runtime: ContentFeedRuntimeDep,
) -> GetContentFeedXmlHandler:
    """Собирает чтение по токену без Console-сессии."""
    return GetContentFeedXmlHandler(runtime.management)


GetContentFeedXmlHandlerDep = Annotated[
    GetContentFeedXmlHandler, Depends(get_content_feed_xml_handler)
]


def get_feed_imports(
    runtime: ContentFeedRuntimeDep,
    tenant: MediaTenantDep,
    context: AuthenticatedRequestContextDep,
) -> FeedImports:
    """Использует те же границы tenant и авторизации, что управление ContentFeed."""
    if tenant_id_from_context(context) != tenant.id:
        raise HTTPException(403, detail={"code": "access_denied"})
    return runtime.imports


FeedImportsDep = Annotated[FeedImports, Depends(get_feed_imports)]


def get_request_feed_import_handler(
    imports: FeedImportsDep,
) -> RequestFeedImportHandler:
    """Собирает отдельный сценарий request_feed_import."""
    return RequestFeedImportHandler(imports)


RequestFeedImportHandlerDep = Annotated[
    RequestFeedImportHandler, Depends(get_request_feed_import_handler)
]


def get_resume_feed_import_handler(imports: FeedImportsDep) -> ResumeFeedImportHandler:
    """Собирает отдельный сценарий resume_feed_import."""
    return ResumeFeedImportHandler(imports)


ResumeFeedImportHandlerDep = Annotated[
    ResumeFeedImportHandler, Depends(get_resume_feed_import_handler)
]


def get_attach_feed_import_handler(imports: FeedImportsDep) -> AttachFeedImportHandler:
    """Собирает отдельный сценарий attach_feed_import."""
    return AttachFeedImportHandler(imports)


AttachFeedImportHandlerDep = Annotated[
    AttachFeedImportHandler, Depends(get_attach_feed_import_handler)
]


def get_resolve_feed_import_handler(
    imports: FeedImportsDep,
) -> ResolveFeedImportHandler:
    """Собирает отдельный сценарий resolve_feed_import."""
    return ResolveFeedImportHandler(imports)


ResolveFeedImportHandlerDep = Annotated[
    ResolveFeedImportHandler, Depends(get_resolve_feed_import_handler)
]


def get_feed_import_handler(imports: FeedImportsDep) -> GetFeedImportHandler:
    """Собирает чтение последней операции без внешнего API."""
    return GetFeedImportHandler(imports)


GetFeedImportHandlerDep = Annotated[
    GetFeedImportHandler, Depends(get_feed_import_handler)
]
