from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def lock_category_tree(
    session: AsyncSession, tenant_id: EntityIdVO, *, shared: bool
) -> None:
    """Удерживает дерево tenant до конца UoW, в том числе при смене основной категории."""
    key = func.hashtextextended(f"catalog:category-tree:{tenant_id.uuid}", 0)
    lock = func.pg_advisory_xact_lock_shared if shared else func.pg_advisory_xact_lock
    await session.execute(select(lock(key)))
