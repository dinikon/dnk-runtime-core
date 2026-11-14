from datetime import timedelta
from src.modules.supplier_sourcing.domain.supplier_source.repository import (
    SupplierSourceRepositoryProtocol,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReferencePort,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierNotFoundError,
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

from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.command import (
    CreateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.dto import (
    CreateSupplierSourceResultDTO,
)
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateSupplierSourceHandler:
    """Создаёт источник через Domain после проверки публичной ссылки CRM."""

    def __init__(
        self,
        repository: SupplierSourceRepositoryProtocol,
        suppliers: SupplierReferencePort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общего UoW и генератор ID."""
        self._repository = repository
        self._suppliers = suppliers
        self._uuid = uuid_generator

    async def execute(
        self, command: CreateSupplierSourceCommand
    ) -> CreateSupplierSourceResultDTO:
        """Защищает компанию от удаления и сохраняет весь агрегат атомарно."""
        supplier = await self._suppliers.get(command.supplier, lock=True)
        if supplier is None:
            raise SupplierNotFoundError("Контрагент поставщика не найден.")
        source = SupplierSource.create(
            identifier=SupplierSourceIdVO.from_value(self._uuid.new()),
            supplier=command.supplier,
            name=SupplierSourceNameVO(command.name),
            fulfillment_modes=command.fulfillment_modes,
            stock_update_policy=command.stock_update_policy.to_value_object(),
            default_lead_time=SupplierLeadTimeVO(
                timedelta(seconds=command.default_lead_time_seconds)
            ),
            external_warehouse_code=(
                ExternalWarehouseCodeVO(command.external_warehouse_code)
                if command.external_warehouse_code is not None
                else None
            ),
        )
        await self._repository.add(source)
        return CreateSupplierSourceResultDTO(
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
