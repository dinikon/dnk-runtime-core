from uuid import UUID
from sqlalchemy import select, func, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel as G,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel as C,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as N,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import (
    SyncRunModel as R,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
)
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingMode,
    BindingClaim,
)
from src.modules.channels.application.catalog_binding.contracts import (
    BindingRecord,
    BindingPairDTO,
    BindingPositionDTO,
    PublicationNodeDTO,
    BindingCandidatesDTO,
    BindingConnectionDTO,
    PublicationStructureDTO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyCatalogBindingQueryRepository:
    """Читает DTO, кандидатов и факты использования без Aggregate restore."""

    def __init__(self, session: AsyncSession) -> None:
        """Не владеет commit и не обращается к Catalog SQL."""
        self.session = session

    async def connection(self, channel_id: UUID) -> BindingConnectionDTO | None:
        """Возвращает только несекретный контекст подключения."""
        row = (
            await self.session.execute(
                select(N.id, C.platform_kind)
                .join(C, C.id == N.channel_id)
                .where(C.id == channel_id)
            )
        ).one_or_none()
        return BindingConnectionDTO(row.id, row.platform_kind) if row else None

    async def records(
        self,
        *,
        catalog_root_id: UUID | None = None,
        connection_id: UUID | None = None,
        group_id: UUID | None = None,
        publication_id: UUID | None = None,
        publication_ids: tuple[UUID, ...] = (),
        mode: BindingMode | None = None,
        offset: int = 0,
        limit: int | None = 25,
    ) -> tuple[tuple[BindingRecord, ...], int]:
        """Читает только проекции и пакет пар после пагинации."""
        filters = []
        if mode is not None:
            filters.append(G.mode == mode.value)
        if catalog_root_id:
            filters.append(G.catalog_root_id == catalog_root_id)
        if connection_id:
            filters.append(G.connection_id == connection_id)
        if group_id:
            filters.append(G.id == group_id)
        if publication_id or publication_ids:
            identifiers = publication_ids or (publication_id,)
            family = select(P.id).where(
                or_(P.id.in_(identifiers), P.parent_id.in_(identifiers))
            )
            filters.append(
                or_(
                    G.publication_root_id.in_(family),
                    G.id.in_(select(I.group_id).where(I.publication_id.in_(family))),
                )
            )
        total = await self.session.scalar(
            select(func.count()).select_from(G).where(*filters)
        )
        rows = (
            (
                await self.session.execute(
                    select(
                        G.__table__,
                        N.channel_id,
                        C.name.label("channel_name"),
                        C.platform_kind,
                    )
                    .join(N, N.id == G.connection_id)
                    .join(C, C.id == N.channel_id)
                    .where(*filters)
                    .order_by(G.created_at.desc(), G.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .mappings()
            .all()
        )
        pairs = (
            (
                await self.session.execute(
                    select(I.__table__)
                    .where(I.group_id.in_([r["id"] for r in rows]))
                    .order_by(I.catalog_position_id)
                )
            )
            .mappings()
            .all()
            if rows
            else ()
        )
        return tuple(
            BindingRecord(
                r["id"],
                r["connection_id"],
                r["channel_id"],
                r["channel_name"],
                r["platform_kind"],
                r["catalog_root_id"],
                BindingMode(r["mode"]),
                r["publication_root_id"],
                r["revision"],
                tuple(
                    BindingPairDTO(v["catalog_position_id"], v["publication_id"])
                    for v in pairs
                    if v["group_id"] == r["id"]
                ),
                r["created_at"],
                r["updated_at"],
            )
            for r in rows
        ), int(total or 0)

    async def nodes(
        self, connection_id: UUID, ids: tuple[UUID, ...], locale: str
    ) -> tuple[PublicationNodeDTO, ...]:
        """Читает затронутые семьи вместе с наблюдаемой конфигурацией."""
        if not ids:
            return ()
        parents = select(P.parent_id).where(
            P.connection_id == connection_id, P.id.in_(ids)
        )
        roots = select(P.id).where(
            P.connection_id == connection_id, or_(P.id.in_(ids), P.id.in_(parents))
        )
        rows = (
            (
                await self.session.execute(
                    select(
                        P.id,
                        P.kind,
                        P.parent_id,
                        P.external_id,
                        P.normalized_data,
                        R.config_revision.label("observed_revision"),
                        N.config_revision.label("current_revision"),
                    )
                    .join(R, R.id == P.last_sync_run_id)
                    .join(N, N.id == P.connection_id)
                    .where(
                        P.connection_id == connection_id,
                        or_(P.id.in_(roots), P.parent_id.in_(roots)),
                    )
                )
            )
            .mappings()
            .all()
        )
        data = {
            r["id"]: PublicationData.from_document(r["normalized_data"]) for r in rows
        }
        stale = {r["id"]: r["observed_revision"] != r["current_revision"] for r in rows}
        result = []
        for row in rows:
            value = data[row["id"]]
            parent = data.get(row["parent_id"])
            stock = parent if value.stock_mode == "parent" and parent else value
            titles = parent.titles if value.inherit_title and parent else value.titles
            result.append(
                PublicationNodeDTO(
                    PublicationStructureDTO(row["id"], row["kind"], row["parent_id"]),
                    BindingPositionDTO(
                        row["id"],
                        row["kind"],
                        next((v.title for v in titles if v.locale == locale), None),
                        value.sku,
                        value.main_image_url,
                        value.status,
                        str(value.price) if value.price is not None else None,
                        value.currency,
                        str(stock.quantity) if stock.quantity is not None else None,
                        value.availability,
                        (
                            row["parent_id"]
                            if value.stock_mode == "parent" and parent
                            else row["id"]
                        ),
                        row["external_id"],
                        stale[row["id"]]
                        or (
                            (value.stock_mode == "parent" or value.inherit_title)
                            and stale.get(row["parent_id"], False)
                        ),
                    ),
                )
            )
        return tuple(result)

    async def claims(
        self, connection_id: UUID, ids: tuple[UUID, ...]
    ) -> tuple[BindingClaim, ...]:
        """Проверяет перекрёстные закрепления заголовков и строк."""
        if not ids:
            return ()
        roots = (
            await self.session.execute(
                select(G.id, G.publication_root_id).where(
                    G.connection_id == connection_id, G.publication_root_id.in_(ids)
                )
            )
        ).all()
        items = (
            await self.session.execute(
                select(I.group_id, I.publication_id)
                .join(G, G.id == I.group_id)
                .where(G.connection_id == connection_id, I.publication_id.in_(ids))
            )
        ).all()
        return tuple(
            BindingClaim(EntityIdVO(v[0]), EntityIdVO(v[1])) for v in (*roots, *items)
        )

    async def used(
        self, catalog_root_id: UUID, position_id: UUID | None = None
    ) -> bool:
        """Проверяет все группы, в том числе архивные и конфликтные."""
        query = select(G.id).where(G.catalog_root_id == catalog_root_id)
        if position_id is not None:
            query = query.where(
                G.id.in_(select(I.group_id).where(I.catalog_position_id == position_id))
            )
        return await self.session.scalar(query.limit(1)) is not None

    async def candidates(
        self,
        connection_id: UUID,
        platform: str,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
    ) -> BindingCandidatesDTO:
        """Фильтрует реальные корни и типы до подсчёта и пагинации."""
        child = P.__table__.alias("binding_child")
        children = exists(select(child.c.id).where(child.c.parent_id == P.id))
        filters = [P.connection_id == connection_id, P.parent_id.is_(None)]
        if mode is BindingMode.VARIABLE_TO_VARIABLE:
            if platform == "rozetka":
                return BindingCandidatesDTO((), (), 0, offset, limit)
            filters.extend(
                [
                    P.kind == ("variable" if platform == "woocommerce" else "simple"),
                    children,
                ]
            )
        else:
            filters.extend([P.kind == "simple", ~children])
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            filters.append(
                or_(
                    P.external_id.ilike("%" + escaped + "%", escape="\\"),
                    P.normalized_data["sku"]
                    .as_string()
                    .ilike("%" + escaped + "%", escape="\\"),
                    P.normalized_data["titles"][locale]
                    .as_string()
                    .ilike("%" + escaped + "%", escape="\\"),
                )
            )
        total = await self.session.scalar(
            select(func.count()).select_from(P).where(*filters)
        )
        ids = tuple(
            (
                await self.session.scalars(
                    select(P.id)
                    .where(*filters)
                    .order_by(P.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )
        nodes = await self.nodes(connection_id, ids, locale)
        claims = await self.claims(connection_id, tuple(v.structure.id for v in nodes))
        occupied = set(v.publication_id.uuid for v in claims)
        occupied_ids = tuple(
            i
            for i in ids
            if i in occupied
            or any(
                v.structure.parent_id == i and v.structure.id in occupied for v in nodes
            )
        )
        positions = {v.structure.id: v.position for v in nodes}
        return BindingCandidatesDTO(
            tuple(positions[i] for i in ids),
            occupied_ids,
            int(total or 0),
            offset,
            limit,
        )
