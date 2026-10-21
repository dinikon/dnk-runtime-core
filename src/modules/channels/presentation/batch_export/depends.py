from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.batch_export.assembly import (
    build_batch_export_handlers,
)
from src.modules.channels.application.batch_export.command.start_batch_export.handler import (
    StartBatchExportHandler,
)


def get_start_batch_export_handler(uow: UoWDep) -> StartBatchExportHandler:
    """Собирает конкретный сценарий на общей tenant-сессии запроса."""
    return build_batch_export_handlers(uow.session, get_plugin_registry()).start


StartBatchExportHandlerDep = Annotated[
    StartBatchExportHandler, Depends(get_start_batch_export_handler)
]
from src.modules.channels.application.batch_export.command.resume_batch_export.handler import (
    ResumeBatchExportHandler,
)


def get_resume_batch_export_handler(uow: UoWDep) -> ResumeBatchExportHandler:
    """Собирает конкретный сценарий на общей tenant-сессии запроса."""
    return build_batch_export_handlers(uow.session, get_plugin_registry()).resume


ResumeBatchExportHandlerDep = Annotated[
    ResumeBatchExportHandler, Depends(get_resume_batch_export_handler)
]
from src.modules.channels.application.batch_export.query.get_batch_export.handler import (
    GetBatchExportHandler,
)


def get_get_batch_export_handler(uow: UoWDep) -> GetBatchExportHandler:
    """Собирает конкретный сценарий на общей tenant-сессии запроса."""
    return build_batch_export_handlers(uow.session, get_plugin_registry()).get


GetBatchExportHandlerDep = Annotated[
    GetBatchExportHandler, Depends(get_get_batch_export_handler)
]
from src.modules.channels.application.batch_export.query.get_batch_export_overview.handler import (
    GetBatchExportOverviewHandler,
)


def get_get_batch_export_overview_handler(uow: UoWDep) -> GetBatchExportOverviewHandler:
    """Собирает конкретный сценарий на общей tenant-сессии запроса."""
    return build_batch_export_handlers(uow.session, get_plugin_registry()).overview


GetBatchExportOverviewHandlerDep = Annotated[
    GetBatchExportOverviewHandler, Depends(get_get_batch_export_overview_handler)
]
from src.modules.channels.application.export_schedule.command.update_export_schedule.handler import (
    UpdateExportScheduleHandler,
)


def get_update_export_schedule_handler(uow: UoWDep) -> UpdateExportScheduleHandler:
    """Собирает конкретный сценарий на общей tenant-сессии запроса."""
    return build_batch_export_handlers(
        uow.session, get_plugin_registry()
    ).update_schedule


UpdateExportScheduleHandlerDep = Annotated[
    UpdateExportScheduleHandler, Depends(get_update_export_schedule_handler)
]
from src.modules.channels.application.product_representation.command.set_publication_export.handler import (
    SetPublicationExportHandler,
)
from src.modules.channels.infrastructure.product_representation.persistence.repository import (
    SqlAlchemyProductRepresentationRepository,
)


def get_set_publication_export_handler(uow: UoWDep) -> SetPublicationExportHandler:
    """Собирает операцию явного разрешения на портах владельцев."""
    return SetPublicationExportHandler(
        build_batch_export_handlers(uow.session, get_plugin_registry()).access,
        SqlAlchemyProductRepresentationRepository(uow.session),
    )


SetPublicationExportHandlerDep = Annotated[
    SetPublicationExportHandler, Depends(get_set_publication_export_handler)
]
