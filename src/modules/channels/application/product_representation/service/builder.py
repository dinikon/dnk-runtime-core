from datetime import datetime
from uuid import UUID

from src.modules.channels.application.catalog_binding.ports import BindingReadPort
from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
    RepresentationBindingSource,
)
from src.modules.channels.application.product_representation.port.catalog import (
    RepresentationCatalogPort,
)
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.value_object import PublicationNode
from src.modules.channels.domain.product_representation.policy import (
    RepresentationPolicy,
)
from src.modules.channels.domain.product_representation.value_object import (
    PublicationContentSnapshot,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RepresentationBuilder:
    """Собирает входы чистой политики; общий путь для preview и будущего экспорта."""

    def __init__(
        self, *, catalog: RepresentationCatalogPort, publications: BindingReadPort
    ) -> None:
        """Получает порты одной внешней транзакции со стабильным снимком."""
        self._catalog = catalog
        self._publications = publications

    async def build(
        self,
        *,
        channel_id: UUID,
        binding: RepresentationBindingSource,
        platform: str,
        config_revision: int,
        locales: tuple[str, ...],
        as_of: datetime,
    ) -> PreparedRepresentation:
        """Читает семью целиком, оставляя правила сопоставления и готовности Domain."""
        family = await self._catalog.family(
            root_id=binding.catalog_root_id, locales=locales, as_of=as_of
        )
        identifiers = tuple(
            dict.fromkeys(
                [item.publication_id for item in binding.items]
                + ([binding.publication_root_id] if binding.publication_root_id else [])
            )
        )
        nodes = await self._publications.nodes(
            binding.connection_id, identifiers, locales[0]
        )
        claims = await self._publications.claims(
            binding.connection_id, tuple(value.structure.id for value in nodes)
        )
        preparation = RepresentationPolicy().prepare(
            group_id=EntityIdVO(binding.id),
            platform=platform,
            mode=binding.mode,
            catalog_root_id=EntityIdVO(binding.catalog_root_id),
            catalog_root=family.root if family else None,
            catalog_positions=family.positions if family else (),
            publication_root_id=(
                EntityIdVO(binding.publication_root_id)
                if binding.publication_root_id
                else None
            ),
            items=tuple(
                CatalogBindingItem.restore(
                    identifier=EntityIdVO(item.id),
                    catalog_position_id=EntityIdVO(item.catalog_position_id),
                    publication_id=EntityIdVO(item.publication_id),
                )
                for item in binding.items
            ),
            publications=tuple(
                PublicationContentSnapshot(
                    structure=PublicationNode(
                        EntityIdVO(value.structure.id),
                        value.structure.kind,
                        (
                            EntityIdVO(value.structure.parent_id)
                            if value.structure.parent_id
                            else None
                        ),
                    ),
                    external_id=value.position.external_id,
                    stale=value.position.stale,
                )
                for value in nodes
            ),
            claims=claims,
        )
        return PreparedRepresentation(
            channel_id=channel_id,
            connection_id=binding.connection_id,
            binding_group_id=binding.id,
            binding_revision=binding.revision,
            config_revision=config_revision,
            platform=platform,
            mode=binding.mode,
            locales=locales,
            as_of=as_of,
            preparation=preparation,
        )
