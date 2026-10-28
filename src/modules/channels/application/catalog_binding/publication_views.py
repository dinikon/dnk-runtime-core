"""Пакетное дополнение существующих карточек публикаций."""

from datetime import datetime
from uuid import UUID
from src.modules.channels.application.catalog_binding.ports import BindingReadPort
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.application.external_publication.representation import (
    PublicationBindingView,
)


class BindingPublicationViews:
    """Собирает состояния групп всей страницы без N+1 по карточкам."""

    def __init__(self, read: BindingReadPort, views: BindingViews) -> None:
        """Принимает read-порты одного tenant UoW."""
        self.read, self.views = read, views

    async def summaries(
        self,
        connection_id: UUID,
        root_ids: tuple[UUID, ...],
        locale: str,
        now: datetime,
    ) -> dict[UUID, tuple[PublicationBindingView, ...]]:
        """Возвращает только локальные ссылки, без изменений источника."""
        if not root_ids:
            return {}
        records, _ = await self.read.records(
            connection_id=connection_id, publication_ids=root_ids, limit=None
        )
        if not records:
            return {}
        groups = await self.views.groups(records, locale, now)
        nodes = await self.read.nodes(connection_id, root_ids, locale)
        families = {
            root: {
                root,
                *(v.structure.id for v in nodes if v.structure.parent_id == root),
            }
            for root in root_ids
        }
        return {
            root: tuple(
                PublicationBindingView(
                    g.group.id,
                    g.group.catalog_root_id,
                    g.preview.catalog.root.title if g.preview.catalog else None,
                    g.group.mode.value,
                    g.preview.assessment.state,
                )
                for g in groups
                if g.group.publication_root_id in family
                or any(p.publication_id in family for p in g.group.items)
            )
            for root, family in families.items()
        }
