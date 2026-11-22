from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import text

from src.modules.catalog.infrastructure.catalog_item.persistence.calculation_reader import (
    SqlAlchemyCatalogCalculationReader,
)
from src.modules.feed_builder.application.feed.query.download_test_csv.handler import (
    DownloadTestCsvHandler,
)
from src.modules.feed_builder.application.feed.query.preview_feed.handler import (
    PreviewFeedHandler,
)
from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportService,
)
from src.modules.feed_builder.infrastructure.feed.serialization.test_csv import (
    TemporaryCsvStorage,
)
from src.modules.feed_builder.infrastructure.publication.catalog.export_values import (
    CatalogExportValues,
)
from src.modules.feed_builder.infrastructure.publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)
from src.modules.feed_builder.presentation.feed.depends import FeedQueryRepositoryDep
from src.modules.feed_builder.presentation.publication.access import (
    require_catalog_subjects,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


async def prepare_export_transaction(uow: UoWDep) -> None:
    """Фиксирует снимок состояния до чтения схемы, прав и ассортимента."""
    await uow.session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))


async def require_catalog_export_access(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> None:
    """Проверяет доступ к коллекции Catalog до раскрытия размера ассортимента."""
    principal = context.principal
    if (
        principal is None
        or principal.tenant_id is None
        or not await authorization.can(
            user_id=UUID(principal.user_id),
            tenant_id=UUID(principal.tenant_id),
            action="catalog.item.read",
            resource_type="catalog.item",
            resource_id=None,
        )
    ):
        raise HTTPException(
            403,
            {
                "code": "SOURCE_ACCESS_DENIED",
                "message": "Недостаточно прав для чтения списка Catalog.",
            },
        )


class _CatalogAccess:
    """Проверяет доступ в текущем запросе и переиспользует проверку общего родителя."""

    def __init__(
        self,
        context: AuthenticatedRequestContextDep,
        authorization: AuthorizationServiceDep,
    ) -> None:
        """Сохраняет доверенный контекст пользователя."""
        self._context = context
        self._authorization = authorization
        self._checked: set[UUID] = set()

    async def ensure_readable(self, identifiers: tuple[UUID, ...]) -> None:
        """Проверяет ещё не проверенные ресурсы Catalog."""
        unchecked = tuple(
            identifier for identifier in identifiers if identifier not in self._checked
        )
        await require_catalog_subjects(self._context, self._authorization, unchecked)
        self._checked.update(unchecked)


def get_publication_export(
    uow: UoWDep,
    feeds: FeedQueryRepositoryDep,
    clock: ClockDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
) -> PublicationExportService:
    """Собирает порты фида, публикаций и Catalog на общей tenant-сессии."""
    return PublicationExportService(
        feeds,
        SqlAlchemyPublicationQueryRepository(uow.session),
        CatalogExportValues(SqlAlchemyCatalogCalculationReader(uow.session)),
        _CatalogAccess(context, authorization),
        clock,
    )


PublicationExportDep = Annotated[
    PublicationExportService, Depends(get_publication_export)
]


def get_preview_feed_handler(export: PublicationExportDep) -> PreviewFeedHandler:
    """Собирает обработчик предпросмотра."""
    return PreviewFeedHandler(export)


def get_download_test_csv_handler(
    export: PublicationExportDep,
) -> DownloadTestCsvHandler:
    """Собирает обработчик пробного файла."""
    return DownloadTestCsvHandler(export, TemporaryCsvStorage())


PreviewFeedHandlerDep = Annotated[PreviewFeedHandler, Depends(get_preview_feed_handler)]
DownloadTestCsvHandlerDep = Annotated[
    DownloadTestCsvHandler, Depends(get_download_test_csv_handler)
]
