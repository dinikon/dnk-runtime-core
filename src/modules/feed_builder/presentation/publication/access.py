from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationQueryRepositoryProtocol,
    PublicationRecord,
)


async def require_catalog_subjects(
    context: RequestContext,
    authorization: AuthorizationServiceProtocol,
    identifiers: tuple[UUID, ...],
) -> None:
    """Проверяет право Catalog для каждого выбранного корня и варианта до отдачи данных."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(403, "Требуется tenant.")
    for identifier in sorted(set(identifiers), key=str):
        if not await authorization.can(
            user_id=UUID(principal.user_id),
            tenant_id=UUID(principal.tenant_id),
            action="catalog.item.read",
            resource_type="catalog.item",
            resource_id=identifier,
        ):
            raise HTTPException(
                403,
                {
                    "code": "SOURCE_ACCESS_DENIED",
                    "message": "Недостаточно прав для позиции Catalog.",
                },
            )


async def require_publication_access(
    identifier: UUID,
    queries: PublicationQueryRepositoryProtocol,
    context: RequestContext,
    authorization: AuthorizationServiceProtocol,
    action: str,
) -> PublicationRecord:
    """Определяет Feed публикации по собственной проекции до выполнения команды."""
    record = await queries.get(identifier)
    if record is None:
        raise HTTPException(
            404, {"code": "PUBLICATION_NOT_FOUND", "message": "Публикация не найдена."}
        )
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=record.feed_id
    )
    await require_feed_access(
        context, authorization, action=action, feed_id=record.feed_id
    )
    return record
