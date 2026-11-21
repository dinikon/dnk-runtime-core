from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.inventory.application.inventory_item.port.physical_usage import (
    PhysicalInventoryUsagePort,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.physical_usage import (
    SqlAlchemyPhysicalInventoryUsage,
)


def get_physical_inventory_usage(uow: UoWDep) -> PhysicalInventoryUsagePort:
    """Подключает факты учётного использования к общей сессии."""
    return SqlAlchemyPhysicalInventoryUsage(uow.session)


PhysicalInventoryUsageDep = Annotated[
    PhysicalInventoryUsagePort, Depends(get_physical_inventory_usage)
]
