from typing import Annotated

from fastapi import Depends

from src.modules.feed_builder.application.publication.command.reset_publication_override.handler import (
    ResetPublicationOverrideHandler,
)
from src.modules.feed_builder.application.publication.command.set_publication_override.handler import (
    SetPublicationOverrideHandler,
)
from src.modules.feed_builder.application.publication.query.get_publication_fields.handler import (
    GetPublicationFieldsHandler,
)
from src.modules.feed_builder.infrastructure.publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)
from src.modules.feed_builder.presentation.feed.depends import FeedRepositoryDep
from src.modules.feed_builder.presentation.feed.export_depends import (
    PublicationExportDep,
)
from src.modules.feed_builder.presentation.publication.depends import PublicationsDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_publication_fields_handler(
    uow: UoWDep, export: PublicationExportDep
) -> GetPublicationFieldsHandler:
    """Собирает чтение карточки на общей tenant-сессии."""
    return GetPublicationFieldsHandler(
        SqlAlchemyPublicationQueryRepository(uow.session), export
    )


def get_set_publication_override_handler(
    feeds: FeedRepositoryDep, publications: PublicationsDep, clock: ClockDep
) -> SetPublicationOverrideHandler:
    """Собирает сценарий сохранения ручного значения в общей транзакции."""
    return SetPublicationOverrideHandler(feeds, publications, clock)


def get_reset_publication_override_handler(
    feeds: FeedRepositoryDep, publications: PublicationsDep, clock: ClockDep
) -> ResetPublicationOverrideHandler:
    """Собирает сценарий сброса ручного значения в общей транзакции."""
    return ResetPublicationOverrideHandler(feeds, publications, clock)


GetPublicationFieldsHandlerDep = Annotated[
    GetPublicationFieldsHandler, Depends(get_publication_fields_handler)
]
SetPublicationOverrideHandlerDep = Annotated[
    SetPublicationOverrideHandler, Depends(get_set_publication_override_handler)
]
ResetPublicationOverrideHandlerDep = Annotated[
    ResetPublicationOverrideHandler, Depends(get_reset_publication_override_handler)
]
