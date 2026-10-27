from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from typing import Any
from src.modules.funnel.domain.aggregate import Funnel
from src.modules.funnel.domain.stage import Stage


class FunnelMapper:
    """Преобразования хранения процесса без I/O и domain-правил."""

    @staticmethod
    def to_domain(row: Mapping[str, Any], stages: list[Mapping[str, Any]]) -> Funnel:
        """Восстанавливает агрегат через фабрики."""
        return Funnel.restore(
            **{
                k: row[k]
                for k in (
                    "id",
                    "model_key",
                    "name",
                    "is_default",
                    "revision",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                )
            },
            stages=tuple(
                Stage.restore(
                    stage_id=s["id"], name=s["name"], color=s["color"], kind=s["kind"]
                )
                for s in stages
            ),
        )

    @staticmethod
    def to_values(entity: Funnel) -> dict[str, Any]:
        """Получает значения заголовка."""
        return {
            k: (value.uuid if isinstance(value, EntityIdVO) else value)
            for k in (
                "id",
                "model_key",
                "name",
                "is_default",
                "revision",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            )
            for value in (getattr(entity, k),)
        }
