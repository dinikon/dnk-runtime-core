from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from typing import Any
from src.modules.crm.domain.deal.aggregate import Deal
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO


class DealMapper:
    """Преобразует представление хранения, не выполняя I/O."""

    @staticmethod
    def to_values(entity: Deal) -> dict[str, Any]:
        """Извлекает собственные поля агрегата и позицию."""
        values = {
            name: getattr(entity, name)
            for name in [
                "id",
                "title",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "source_lead_id",
                "source_lead_snapshot",
                "lifecycle_state",
            ]
        }
        values.update(
            funnel_id=entity.position.funnel_id,
            stage_id=entity.position.stage_id,
            position_revision=entity.position.revision,
        )
        return {
            k: (v.uuid if isinstance(v, EntityIdVO) else v) for k, v in values.items()
        }

    @staticmethod
    def to_domain(row: Mapping[str, Any], **related: object) -> Deal:
        """Восстанавливает агрегат через его явную фабрику."""
        values = {
            name: row[name]
            for name in [
                "id",
                "title",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "source_lead_id",
                "source_lead_snapshot",
                "lifecycle_state",
            ]
        }
        return Deal.restore(
            **values,
            position=FunnelPositionVO(
                row["funnel_id"], row["stage_id"], row["position_revision"]
            ),
            **related,
        )
