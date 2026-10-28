"""Подготовка зависимостей согласованного изменения дерева публикаций."""

from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.sync_run.port.source import PublicationObservation
from src.modules.channels.domain.external_publication.repository import (
    ExternalPublicationRepositoryProtocol,
)


class PublicationChangePreparation:
    """Просит источник подтвердить старое дерево при изменении ролей."""

    def __init__(self, publications: ExternalPublicationRepositoryProtocol) -> None:
        """Получает repository короткой транзакции без внешнего API."""
        self.publications = publications

    async def dependency_keys(
        self, *, connection_id: UUID, observations: tuple[PublicationObservation, ...]
    ) -> tuple[tuple[str, str], ...]:
        """Возвращает недостающие нативные объекты, не исправляя связи догадками."""
        incoming = {item.key: item for item in observations}
        existing = await self.publications.by_keys(
            EntityIdVO.from_value(connection_id), tuple(incoming)
        )
        changed_roles = tuple(
            item.id
            for item in existing
            if item.kind != incoming[(item.resource_type, item.external_id)].kind
        )
        if not changed_roles:
            return ()
        affected = await self.publications.affected_tree(
            EntityIdVO.from_value(connection_id), changed_roles
        )
        return tuple(
            sorted(
                {(item.resource_type, item.external_id) for item in affected}
                - set(incoming)
            )
        )
