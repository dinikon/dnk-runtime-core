from pydantic import BaseModel
from src.modules.channels.application.product_representation.query.get_representation.dto import (
    GetRepresentationResultDTO,
)
from src.modules.channels.presentation.product_representation.http.response.fields import (
    RepresentationStateResponse,
    RepresentationBindingItemResponse,
)


class GetRepresentationResponse(BaseModel):
    """Состояние редактора и устойчивые идентификаторы сопоставленных позиций."""

    state: RepresentationStateResponse
    binding_revision: int
    config_revision: int
    locales: tuple[str, ...]
    items: tuple[RepresentationBindingItemResponse, ...]

    @classmethod
    def from_dto(
        cls, result: GetRepresentationResultDTO
    ) -> "GetRepresentationResponse":
        """Возвращает все языки overrides и актуальные ревизии без секретов."""
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
