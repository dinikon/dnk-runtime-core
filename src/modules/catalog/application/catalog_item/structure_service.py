from datetime import datetime
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.application.catalog_item.structure_input import (
    VariableStructureInput,
)
from src.modules.catalog.application.catalog_item.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.domain.error import InvalidCatalogValueError


class CatalogItemStructureService:
    """Координирует идентичности и снимки; комбинации проверяет корень."""

    def __init__(
        self, definitions: AttributeDefinitionsPort, uuid: UUIdGeneratorProtocol
    ) -> None:
        """Принимает публичные порты определений и генерации UUID."""
        self._definitions = definitions
        self._uuid = uuid

    async def prepare(
        self,
        value: VariableStructureInput,
        root_id: CatalogItemIdVO,
        actor: EntityIdVO,
        now: datetime,
        root: CatalogItem | None = None,
    ) -> tuple[tuple[CatalogItem, ...], tuple[EnumAttributeSnapshot, ...]]:
        """Сохраняет own-данные существующих детей и назначает ID только новым."""
        definitions = await self._definitions.get_definitions(
            tuple(a.attribute_id for a in value.axes)
        )
        children = []
        for value_item in value.variants:
            if value_item.item_id is not None:
                if root is None:
                    raise InvalidCatalogValueError(
                        "ID нового варианта назначает сервер."
                    )
                children.append(
                    root.prepare_variant(
                        value_item.item_id, value_item.selection, actor, now
                    )
                )
            else:
                children.append(
                    CatalogItem.create_variant(
                        CatalogItemIdVO(self._uuid.new()),
                        root_id,
                        value_item.selection,
                        actor,
                        now,
                    )
                )
        return tuple(children), definitions
