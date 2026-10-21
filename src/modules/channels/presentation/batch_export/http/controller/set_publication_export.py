from dataclasses import asdict
from uuid import UUID
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError

from src.modules.channels.presentation.depends.access import CatalogLinkContextDep
from src.modules.channels.presentation.batch_export.depends import (
    SetPublicationExportHandlerDep,
)
from src.modules.channels.presentation.batch_export.http.request.set_publication_export import (
    SetPublicationExportRequest,
)
from src.modules.channels.presentation.batch_export.http.response.set_publication_export import (
    SetPublicationExportResponse,
)
from src.modules.channels.application.product_representation.command.set_publication_export.command import (
    SetPublicationExportCommand,
    RepresentationExportRefDTO,
)


async def set_publication_export(
    channel_id: UUID,
    payload: SetPublicationExportRequest,
    context: CatalogLinkContextDep,
    handler: SetPublicationExportHandlerDep,
) -> SetPublicationExportResponse:
    """Разрешает экспорт на выбранных представлениях с атомарной проверкой версий."""
    try:
        return SetPublicationExportResponse(
            **asdict(
                await handler.execute(
                    SetPublicationExportCommand(
                        channel_id,
                        payload.enabled,
                        tuple(
                            RepresentationExportRefDTO(
                                v.representation_id, v.expected_revision
                            )
                            for v in payload.items
                        ),
                    )
                )
            )
        )
    except ChannelsError as error:
        raise http_error(error) from error
