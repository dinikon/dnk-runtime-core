from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from typing import Any
from src.modules.crm.domain.lead.aggregate import Lead
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO


class LeadMapper:
    """Преобразует представление хранения, не выполняя I/O."""

    @staticmethod
    def to_values(entity: Lead) -> dict[str, Any]:
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
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
                "conversion_result",
                "conversion_key",
                "conversion_fingerprint",
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
    def to_domain(row: Mapping[str, Any], **related: object) -> Lead:
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
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
                "conversion_result",
                "conversion_key",
                "conversion_fingerprint",
            ]
        }
        return Lead.restore(
            **values,
            position=FunnelPositionVO(
                row["funnel_id"], row["stage_id"], row["position_revision"]
            ),
            **related,
        )
