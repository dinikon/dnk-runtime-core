from datetime import timedelta
from src.modules.supplier_sourcing.domain.supplier_source.repository import (
    SupplierSourceRepositoryProtocol,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReferencePort,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierNotFoundError,
    SupplierSourceNotFoundError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
    SupplierSourceNameVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.external_warehouse_code import (
    ExternalWarehouseCodeVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)

from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.command import (
    UpdateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.dto import (
    UpdateSupplierSourceResultDTO,
)


class UpdateSupplierSourceHandler:
    """Меняет карточку существующими Domain-методами внутри внешнего UoW."""

    def __init__(
        self,
        repository: SupplierSourceRepositoryProtocol,
        suppliers: SupplierReferencePort,
    ) -> None:
        """Принимает write-порт и публичный порт поставщиков."""
        self._repository = repository
        self._suppliers = suppliers

    async def execute(
        self, command: UpdateSupplierSourceCommand
    ) -> UpdateSupplierSourceResultDTO:
        """Блокирует корень, объединяет PATCH с текущими настройками и сохраняет один раз."""
        current = await self._repository.get_for_update(command.source_id)
        if current is None:
            raise SupplierSourceNotFoundError("Источник поставщика не найден.")
        supplier = await self._suppliers.get(current.supplier, lock=True)
        if supplier is None:
            raise SupplierNotFoundError("Контрагент поставщика не найден.")
        source = current
        if "name" in command.fields and command.name is not None:
            source = source.rename(SupplierSourceNameVO(command.name))
        if "external_warehouse_code" in command.fields:
            source = source.change_external_warehouse_code(
                ExternalWarehouseCodeVO(command.external_warehouse_code)
                if command.external_warehouse_code is not None
                else None
            )
        if {"fulfillment_modes", "default_lead_time_seconds"} & command.fields:
            source = source.configure_fulfillment(
                fulfillment_modes=(
                    command.fulfillment_modes
                    if command.fulfillment_modes is not None
                    else current.fulfillment_modes
                ),
                default_lead_time=(
                    SupplierLeadTimeVO(
                        timedelta(seconds=command.default_lead_time_seconds)
                    )
                    if command.default_lead_time_seconds is not None
                    else current.default_lead_time
                ),
            )
        if (
            "stock_update_policy" in command.fields
            and command.stock_update_policy is not None
        ):
            source = source.change_stock_update_policy(
                command.stock_update_policy.to_value_object()
            )
        if "is_active" in command.fields:
            source = source.activate() if command.is_active else source.deactivate()
        if source != current:
            await self._repository.save(source)
        return UpdateSupplierSourceResultDTO(
            id=source.id.uuid,
            supplier_model_key=source.supplier.model_key,
            supplier_id=source.supplier.identifier.uuid,
            name=source.name.value,
            external_warehouse_code=(
                source.external_warehouse_code.value
                if source.external_warehouse_code is not None
                else None
            ),
            fulfillment_modes=tuple(sorted(source.fulfillment_modes)),
            default_lead_time_seconds=source.default_lead_time.value
            // timedelta(seconds=1),
            is_active=source.is_active,
            stock_ttl_seconds=source.stock_update_policy.ttl // timedelta(seconds=1),
            stale_behavior=source.stock_update_policy.stale_behavior,
            missing_sku_behavior=source.stock_update_policy.missing_sku_behavior,
            supplier_name=supplier.name,
        )
