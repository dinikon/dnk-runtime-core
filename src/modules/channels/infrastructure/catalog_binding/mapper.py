"""Преобразование представления хранения без бизнес-правил и SQL."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID
from sqlalchemy.engine import RowMapping
from src.modules.channels.domain.catalog_binding.aggregate import CatalogBindingGroup
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogBindingMapper:
    """Domain восстанавливается исключительно через явные фабрики."""

    @staticmethod
    def to_domain(row: RowMapping, items: Sequence[RowMapping]) -> CatalogBindingGroup:
        """Передаёт представление фабрикам корня и дочерних Entity."""
        return CatalogBindingGroup.restore(
            identifier=EntityIdVO(row["id"]),
            connection_id=EntityIdVO(row["connection_id"]),
            catalog_root_id=EntityIdVO(row["catalog_root_id"]),
            mode=BindingMode(row["mode"]),
            publication_root_id=(
                EntityIdVO(row["publication_root_id"])
                if row["publication_root_id"]
                else None
            ),
            revision=row["revision"],
            items=tuple(
                CatalogBindingItem.restore(
                    identifier=EntityIdVO(v["id"]),
                    catalog_position_id=EntityIdVO(v["catalog_position_id"]),
                    publication_id=EntityIdVO(v["publication_id"]),
                )
                for v in items
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
        )

    @staticmethod
    def to_insert_values(
        group: CatalogBindingGroup,
    ) -> dict[str, UUID | str | int | datetime | None]:
        """Подготавливает только собственные поля агрегата."""
        return dict(
            id=group.id.uuid,
            connection_id=group.connection_id.uuid,
            catalog_root_id=group.catalog_root_id.uuid,
            mode=group.mode.value,
            publication_root_id=(
                group.publication_root_id.uuid if group.publication_root_id else None
            ),
            revision=group.revision,
            created_at=group.created_at,
            updated_at=group.updated_at,
            created_by=group.created_by.uuid,
            updated_by=group.updated_by.uuid,
        )
