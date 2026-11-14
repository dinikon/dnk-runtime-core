from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.crm.application.counterparty_reference.source_usage import (
    CounterpartySourceUsagePort,
)
from src.modules.crm.infrastructure.counterparty_reference.source_usage import (
    SupplierSourceCounterpartyUsageAdapter,
)
from src.modules.supplier_sourcing.infrastructure.supplier_source.persistence.supplier_usage import (
    SqlAlchemySupplierSourceUsage,
)


def get_counterparty_source_usage(uow: UoWDep) -> CounterpartySourceUsagePort:
    """Подключает публичный порт Supplier Sourcing к общей транзакции удаления CRM."""
    return SupplierSourceCounterpartyUsageAdapter(
        SqlAlchemySupplierSourceUsage(uow.session)
    )


CounterpartySourceUsageDep = Annotated[
    CounterpartySourceUsagePort, Depends(get_counterparty_source_usage)
]
