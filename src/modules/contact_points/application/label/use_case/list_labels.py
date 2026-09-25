from src.modules.contact_points.application.label.query.list_labels_query import (
    ListContactPointLabelsQuery,
)
from src.modules.contact_points.application.label.dto.label_dto import (
    ContactPointLabelDTO,
    label_dto,
)
from src.modules.contact_points.domain.label.repository import (
    ContactPointLabelRepositoryProtocol,
)


class ListContactPointLabelsUseCase:
    """Возвращает доступные подписи, включая архивные для существующих связей."""

    def __init__(self, repository: ContactPointLabelRepositoryProtocol):
        self.repository = repository

    async def __call__(
        self, query: ListContactPointLabelsQuery
    ) -> tuple[ContactPointLabelDTO, ...]:
        """Читает настройки только текущего tenant."""
        return tuple(
            label_dto(label)
            for label in await self.repository.list(query.tenant_id, query.type)
        )


__all__ = ["ListContactPointLabelsUseCase"]
