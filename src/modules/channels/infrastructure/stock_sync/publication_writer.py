from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.external_publication.repository import (
    ExternalPublicationRepositoryProtocol,
)
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.types import JsonObject
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PublicationStockWriter:
    """Узкое применение через агрегаты ExternalPublication."""

    def __init__(self, publications: ExternalPublicationRepositoryProtocol) -> None:
        """Получает Domain repository того же UoW."""
        self.publications = publications

    async def apply(
        self,
        *,
        connection_id: UUID,
        publication_id: UUID,
        owner_id: UUID,
        stock: StockSnapshotVO,
        platform_data: JsonObject,
        now: datetime,
        config_revision: int,
    ) -> None:
        """Родительское количество не копируется в собственное количество ребёнка."""
        tree = await self.publications.affected_tree(
            EntityIdVO(connection_id),
            tuple(EntityIdVO(v) for v in {publication_id, owner_id}),
        )
        owner = next((v for v in tree if v.id.uuid == owner_id), None)
        if owner is None or (owner.resource_type, owner.external_id) != (
            stock.resource_type,
            stock.external_id,
        ):
            raise StockSyncError("stock_ownership_ambiguous")
        owner.observe_stock(
            quantity=stock.quantity,
            stock_mode=stock.mode,
            availability=stock.availability,
            native={
                "stock": stock.to_document(),
                "native": platform_data,
                "config_revision": config_revision,
            },
            now=now,
        )
        await self.publications.save(owner)
        child = next(
            (v for v in tree if v.id.uuid == publication_id and v.id.uuid != owner_id),
            None,
        )
        if child is not None:
            if child.parent_id != owner.id:
                raise StockSyncError("stock_ownership_ambiguous")
            child.observe_stock(
                quantity=None,
                stock_mode="parent",
                availability=stock.availability,
                native={"owner_publication_id": str(owner_id)},
                now=now,
            )
            await self.publications.save(child)
