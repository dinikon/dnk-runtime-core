from src.modules.catalog.application.product.structure_input import (
    SimpleStructureInput,
    VariableStructureInput,
    VariantStructureInput,
)
from src.modules.catalog.application.product.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.entity.structure import (
    SimpleProductStructure,
    VariableProductStructure,
)
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class ProductStructureService:
    """Координирует генерацию идентичностей и чтение снимков для структуры."""

    def __init__(
        self, definitions: AttributeDefinitionsPort, uuid: UUIdGeneratorProtocol
    ) -> None:
        """Принимает порты определений и генератора ID без SQL-зависимостей."""
        self._definitions = definitions
        self._uuid = uuid

    def _variant(
        self, value: VariantStructureInput, product: Product | None
    ) -> Variant:
        """Генерирует новый ID либо разрешает существующую позицию через Product."""
        if value.variant_id is not None:
            if product is None:
                raise InvalidCatalogValueError("ID новой позиции назначает сервер.")
            product.find_variant(value.variant_id)
        identifier = value.variant_id or VariantIdVO(self._uuid.new())
        return Variant.create(identifier, value.virtual, value.selection)

    async def prepare(
        self,
        value: SimpleStructureInput | VariableStructureInput,
        product: Product | None = None,
    ) -> tuple[
        SimpleProductStructure | VariableProductStructure,
        tuple[EnumAttributeSnapshot, ...],
    ]:
        """Готовит данные; полные инварианты структуры проверит Product."""
        if isinstance(value, SimpleStructureInput):
            return (
                SimpleProductStructure.create(self._variant(value.variant, product)),
                (),
            )
        definitions = await self._definitions.get_definitions(
            tuple(a.attribute_id for a in value.axes)
        )
        structure = VariableProductStructure.create(
            value.axes,
            value.default_selection,
            tuple(self._variant(v, product) for v in value.variants),
        )
        return structure, definitions
