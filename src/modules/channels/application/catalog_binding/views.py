"""Пакетная сборка read-проекций и единого контекста редактора."""

from collections import Counter
from hashlib import sha256
import json
from datetime import datetime
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import (
    BindingPairDTO,
    BindingPreviewDTO,
    BindingGroupDTO,
    BindingRecord,
    CatalogFamilyDTO,
    PublicationNodeDTO,
)
from src.modules.channels.application.catalog_binding.ports import (
    BindingCatalogPort,
    BindingReadPort,
)
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.policy import BindingStructurePolicy
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingMode,
    BindingClaim,
    CatalogFamily,
    PublicationNode,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class BindingViews:
    """Не восстанавливает write агрегаты и не изменяет состояние."""

    def __init__(self, catalog: BindingCatalogPort, read: BindingReadPort) -> None:
        """Получает порты одного tenant UoW."""
        self.catalog, self.read = catalog, read

    async def preview(
        self,
        *,
        connection_id: UUID,
        platform: str,
        catalog_root_id: UUID,
        mode: BindingMode,
        publication_root_id: UUID | None,
        items: tuple[BindingPairDTO, ...],
        locale: str,
        now: datetime,
        group_id: UUID | None = None,
    ) -> BindingPreviewDTO:
        """Собирает ограниченный контекст одного предложения."""
        families = await self.catalog.families((catalog_root_id,), locale, now)
        catalog = families[0] if families else None
        ids = tuple(
            {
                *(v.publication_id for v in items),
                *(() if publication_root_id is None else (publication_root_id,)),
            }
        )
        nodes = await self.read.nodes(connection_id, ids, locale)
        claims = await self.read.claims(
            connection_id, tuple(v.structure.id for v in nodes)
        )
        return self.build(
            catalog=catalog,
            nodes=nodes,
            claims=claims,
            platform=platform,
            catalog_root_id=catalog_root_id,
            mode=mode,
            publication_root_id=publication_root_id,
            items=items,
            group_id=group_id,
        )

    @staticmethod
    def build(
        *,
        catalog: "CatalogFamilyDTO | None",
        nodes: tuple["PublicationNodeDTO", ...],
        claims: tuple["BindingClaim", ...],
        platform: str,
        catalog_root_id: UUID,
        mode: BindingMode,
        publication_root_id: UUID | None,
        items: tuple[BindingPairDTO, ...],
        group_id: UUID | None,
    ) -> BindingPreviewDTO:
        """Вычисляет состояние, токены структуры и только однозначные SKU-подсказки."""
        pairs = tuple(
            CatalogBindingItem.restore(
                identifier=EntityIdVO(v.publication_id),
                catalog_position_id=EntityIdVO(v.catalog_position_id),
                publication_id=EntityIdVO(v.publication_id),
            )
            for v in items
        )
        assessment = BindingStructurePolicy().assess(
            mode=mode,
            catalog_root_id=EntityIdVO(catalog_root_id),
            catalog=(
                CatalogFamily(
                    EntityIdVO(catalog.structure.id),
                    catalog.structure.kind,
                    tuple(EntityIdVO(v) for v in catalog.structure.positions),
                )
                if catalog
                else None
            ),
            publication_root_id=(
                EntityIdVO(publication_root_id) if publication_root_id else None
            ),
            items=pairs,
            nodes=tuple(
                PublicationNode(
                    EntityIdVO(v.structure.id),
                    v.structure.kind,
                    (
                        EntityIdVO(v.structure.parent_id)
                        if v.structure.parent_id
                        else None
                    ),
                )
                for v in nodes
            ),
            claims=claims,
            platform=platform,
            group_id=EntityIdVO(group_id) if group_id else None,
        )
        left = (
            [
                str(catalog.structure.id),
                catalog.structure.kind,
                sorted(str(v) for v in catalog.structure.positions),
            ]
            if catalog
            else None
        )
        right = sorted(
            (
                str(v.structure.id),
                v.structure.kind,
                str(v.structure.parent_id) if v.structure.parent_id else None,
            )
            for v in nodes
        )
        catalog_token = sha256(json.dumps(left).encode()).hexdigest()
        publication_token = sha256(json.dumps(right).encode()).hexdigest()
        positions = tuple(
            v.position
            for v in nodes
            if (
                v.structure.parent_id == publication_root_id
                and publication_root_id is not None
            )
            or (
                v.structure.id == publication_root_id
                and (mode is BindingMode.SIMPLE_TO_SIMPLE or platform == "prom")
            )
            or (
                mode is BindingMode.VARIABLE_TO_SIMPLE
                and v.structure.id in {p.publication_id for p in items}
            )
        )
        suggestions: list[BindingPairDTO] = []
        if catalog:
            lcounts = Counter(v.sku for v in catalog.positions if v.sku)
            rcounts = Counter(v.sku for v in positions if v.sku)
            occupied = {
                v.publication_id.uuid for v in claims if v.group_id.uuid != group_id
            }
            for l in catalog.positions:
                for r in positions:
                    if (
                        l.sku
                        and l.sku == r.sku
                        and lcounts[l.sku] == rcounts[l.sku] == 1
                        and r.id not in occupied
                    ):
                        suggestions.append(BindingPairDTO(l.id, r.id))
        return BindingPreviewDTO(
            catalog,
            positions,
            assessment,
            catalog_token,
            publication_token,
            tuple(suggestions),
        )

    async def groups(
        self, records: tuple[BindingRecord, ...], locale: str, now: datetime
    ) -> tuple[BindingGroupDTO, ...]:
        """Загружает Catalog и публикации на группу подключений, без N+1 по карточкам."""
        families = {
            v.structure.id: v
            for v in await self.catalog.families(
                tuple({v.catalog_root_id for v in records}), locale, now
            )
        }
        result: list[BindingGroupDTO] = []
        for connection_id in dict.fromkeys(v.connection_id for v in records):
            batch = tuple(v for v in records if v.connection_id == connection_id)
            ids = tuple(
                {
                    identifier
                    for v in batch
                    for identifier in (
                        *[p.publication_id for p in v.items],
                        *(
                            ()
                            if v.publication_root_id is None
                            else (v.publication_root_id,)
                        ),
                    )
                }
            )
            nodes = await self.read.nodes(connection_id, ids, locale)
            claims = await self.read.claims(
                connection_id, tuple(v.structure.id for v in nodes)
            )
            for record in batch:
                scoped = self.scope_nodes(
                    nodes,
                    tuple(p.publication_id for p in record.items),
                    record.publication_root_id,
                )
                preview = self.build(
                    catalog=families.get(record.catalog_root_id),
                    nodes=scoped,
                    claims=claims,
                    platform=record.platform,
                    catalog_root_id=record.catalog_root_id,
                    mode=record.mode,
                    publication_root_id=record.publication_root_id,
                    items=record.items,
                    group_id=record.id,
                )
                result.append(BindingGroupDTO(record, preview))
        order = {v.id: i for i, v in enumerate(records)}
        return tuple(sorted(result, key=lambda v: order[v.group.id]))

    @staticmethod
    def scope_nodes(
        nodes: tuple["PublicationNodeDTO", ...],
        publications: tuple[UUID, ...],
        root: UUID | None,
    ) -> tuple["PublicationNodeDTO", ...]:
        """Не включает чужие семьи в структурный токен конкретной группы."""
        direct = set(publications) | ({root} if root else set())
        parents = {
            v.structure.parent_id
            for v in nodes
            if v.structure.id in direct and v.structure.parent_id
        }
        roots = direct | parents
        return tuple(
            v
            for v in nodes
            if v.structure.id in roots or v.structure.parent_id in roots
        )
