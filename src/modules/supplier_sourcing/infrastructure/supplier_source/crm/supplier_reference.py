from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)

from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.crm.application.counterparty_reference.service import (
    CounterpartyReferenceService,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReference,
)


class CrmSupplierReferenceAdapter:
    """Переводит публичные ссылки CRM в составные ссылки Supplier Sourcing."""

    def __init__(self, counterparties: CounterpartyReferenceService) -> None:
        """Принимает Application-контракт CRM, без чужих ORM/Domain-моделей."""
        self._counterparties = counterparties

    async def get(
        self, supplier: SupplierReferenceVO, *, lock: bool = False
    ) -> SupplierReference | None:
        """Проверяет выбранный тип контрагента с защитой от конкурентного удаления."""
        party = await self._counterparties.get(
            CounterpartyModelKey(supplier.model_key.value),
            supplier.identifier.uuid,
            lock=lock,
        )
        return (
            SupplierReference(supplier, party.display_name)
            if party is not None
            else None
        )

    async def get_many(
        self, suppliers: tuple[SupplierReferenceVO, ...]
    ) -> dict[SupplierReferenceVO, SupplierReference]:
        """Сохраняет тип в ключах, даже когда UUID компании и контакта одинаковы."""
        parties = await self._counterparties.get_many(
            tuple(
                (
                    CounterpartyModelKey(supplier.model_key.value),
                    supplier.identifier.uuid,
                )
                for supplier in suppliers
            )
        )
        return {
            supplier: SupplierReference(
                supplier,
                parties[
                    (
                        CounterpartyModelKey(supplier.model_key.value),
                        supplier.identifier.uuid,
                    )
                ].display_name,
            )
            for supplier in suppliers
            if (
                CounterpartyModelKey(supplier.model_key.value),
                supplier.identifier.uuid,
            )
            in parties
        }
