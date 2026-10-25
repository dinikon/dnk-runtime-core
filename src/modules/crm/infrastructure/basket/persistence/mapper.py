from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from typing import Any
from src.modules.crm.domain.basket.aggregate import Basket
from src.modules.crm.domain.basket.entity.item import BasketItem


class BasketMapper:
    """Преобразования корзины без правил жизненного цикла и I/O."""

    @staticmethod
    def to_domain(row: Mapping[str, Any], items: list[Mapping[str, Any]]) -> Basket:
        """Восстанавливает весь агрегат вместе с внутренними строками."""
        return Basket.restore(
            basket_id=row["id"],
            owner_model_key=row["owner_model_key"],
            owner_record_id=row["owner_record_id"],
            currency=row["currency"],
            revision=row["revision"],
            state=row["state"],
            source_basket_id=row["source_basket_id"],
            items=tuple(
                BasketItem.restore(
                    item_id=i["id"],
                    **{
                        k: i[k]
                        for k in (
                            "name",
                            "kind",
                            "catalog_item_id",
                            "sku",
                            "quantity",
                            "unit",
                            "unit_price",
                            "custom_fields",
                        )
                    },
                )
                for i in items
            ),
        )

    @staticmethod
    def to_values(entity: Basket) -> dict[str, Any]:
        """Извлекает состояние для хранения."""
        return {
            k: (value.uuid if isinstance(value, EntityIdVO) else value)
            for k in (
                "id",
                "owner_model_key",
                "owner_record_id",
                "currency",
                "total",
                "state",
                "revision",
                "source_basket_id",
            )
            for value in (getattr(entity, k),)
        }
