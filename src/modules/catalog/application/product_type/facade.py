from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.entity.content_block import ContentBlock
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.domain.product_type.value_object.defaults import (
    DEFAULT_BLOCKS,
    DEFAULT_PRODUCT_TYPE_CODE,
    DEFAULT_TYPE_LABELS,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogProvisioningFacade:
    """Публичный Application-фасад установки системной схемы нового tenant."""

    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает порты, собранные на общей tenant-сессии onboarding."""
        self._repository = repository
        self._uuid = uuid
        self._clock = clock

    async def initialize_defaults(
        self, tenant_id: EntityIdVO, actor_id: EntityIdVO
    ) -> None:
        """Устанавливает Default либо проверяет существующую схему без смены UUID."""
        existing = await self._repository.get_by_code(DEFAULT_PRODUCT_TYPE_CODE)
        if existing is not None:
            existing.ensure_default()
            return
        product_type = ProductType.create(
            EntityIdVO(self._uuid.new()),
            DEFAULT_PRODUCT_TYPE_CODE,
            tuple(
                ContentBlock.create(
                    EntityIdVO(self._uuid.new()),
                    code,
                    value_type,
                    required,
                    position,
                    labels,
                )
                for position, (code, value_type, required, labels) in enumerate(
                    DEFAULT_BLOCKS
                )
            ),
            DEFAULT_TYPE_LABELS,
            actor_id,
            self._clock.now(),
        )
        await self._repository.add(product_type)
