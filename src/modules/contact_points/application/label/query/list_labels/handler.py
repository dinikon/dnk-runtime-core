from src.modules.contact_points.application.label.query.list_labels.query import (
    ListContactPointLabelsQuery,
)
from src.modules.contact_points.application.label.query.list_labels.dto import (
    ListContactPointLabelDTO,
    label_dto,
)
from src.modules.contact_points.domain.label.repository import (
    ContactPointLabelRepositoryProtocol,
)


class ListContactPointLabelsHandler:
    """Возвращает доступные подписи, включая архивные для существующих связей."""

    def __init__(self, repository: ContactPointLabelRepositoryProtocol):
        self.repository = repository

    async def execute(
        self, query: ListContactPointLabelsQuery
    ) -> tuple[ListContactPointLabelDTO, ...]:
        """Читает настройки только текущего tenant."""
        labels = await self.repository.list(query.tenant_id, query.type)
        ordered = sorted(
            labels,
            key=lambda label: (label.type, label.name.value.casefold(), str(label.id)),
        )
        return tuple(label_dto(label) for label in ordered)


__all__ = ["ListContactPointLabelsHandler"]
