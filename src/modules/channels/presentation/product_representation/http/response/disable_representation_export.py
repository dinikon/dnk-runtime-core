from pydantic import BaseModel
from src.modules.channels.application.product_representation.command.disable_representation_export.dto import (
    DisableRepresentationExportResultDTO,
)
from src.modules.channels.presentation.product_representation.http.response.fields import (
    RepresentationStateResponse,
    RepresentationBindingItemResponse,
)


class DisableRepresentationExportResponse(BaseModel):
    """Публичный ответ отдельного HTTP-сценария disable_representation_export."""

    state: RepresentationStateResponse
    binding_revision: int
    config_revision: int
    locales: tuple[str, ...]
    items: tuple[RepresentationBindingItemResponse, ...]

    @classmethod
    def from_dto(
        cls, result: DisableRepresentationExportResultDTO
    ) -> "DisableRepresentationExportResponse":
        """Явно перечисляет поля своего результата и пары текущей группы."""
        return cls(
            state=RepresentationStateResponse.from_state(result.state),
            binding_revision=result.binding_revision,
            config_revision=result.config_revision,
            locales=result.locales,
            items=tuple(
                RepresentationBindingItemResponse(
                    id=item.id,
                    catalog_position_id=item.catalog_position_id,
                    publication_id=item.publication_id,
                )
                for item in result.items
            ),
        )
