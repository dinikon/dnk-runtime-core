from uuid import UUID, uuid5
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO

_JOB_NAMESPACE = UUID("bb04b5ea-0a10-4e36-93b9-40b77dbfa348")


def deterministic_job_id(
    tenant_id: EntityIdVO,
    price_list_id: PriceListIdVO,
    schedule_revision: int,
    planned_at: str,
) -> EntityIdVO:
    return EntityIdVO(
        uuid5(
            _JOB_NAMESPACE,
            f"{tenant_id}:{price_list_id}:{schedule_revision}:{planned_at}",
        )
    )


def deterministic_cleanup_job_id(tenant_id: EntityIdVO, planned_at: str) -> EntityIdVO:
    return EntityIdVO(
        uuid5(_JOB_NAMESPACE, f"{tenant_id}:price-list-cleanup:{planned_at}")
    )


__all__ = ["deterministic_job_id", "deterministic_cleanup_job_id"]
