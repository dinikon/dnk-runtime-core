from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.basket.entity.item import BasketItem
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError


@dataclass(slots=True)
class Basket:
    """Единственный коммерческий состав владельца, с собственным жизненным циклом."""

    id: EntityIdVO
    owner_model_key: str
    owner_record_id: EntityIdVO
    currency: str
    items: tuple[BasketItem, ...]
    revision: int
    state: str
    source_basket_id: EntityIdVO | None

    @classmethod
    def create(
        cls,
        *,
        basket_id: EntityIdVO,
        owner_model_key: str,
        owner_record_id: EntityIdVO,
        currency: str,
        items: tuple[BasketItem, ...] = (),
        source_basket_id: EntityIdVO | None = None,
    ) -> Self:
        """Создаёт собственную редактируемую корзину проверенного владельца."""
        cls._validate(currency, items)
        if owner_model_key not in ("crm.lead", "crm.deal"):
            raise SalesError("Неизвестный владелец корзины.")
        return cls(
            EntityIdVO.from_value(basket_id),
            owner_model_key,
            EntityIdVO.from_value(owner_record_id),
            currency,
            items,
            1,
            "editable",
            EntityIdVO.from_value(source_basket_id) if source_basket_id else None,
        )

    @classmethod
    def restore(
        cls,
        *,
        basket_id: EntityIdVO,
        owner_model_key: str,
        owner_record_id: EntityIdVO,
        currency: str,
        items: tuple[BasketItem, ...],
        revision: int,
        state: str,
        source_basket_id: EntityIdVO | None,
    ) -> Self:
        """Восстанавливает агрегат и проверяет сохранённые инварианты."""
        result = cls.create(
            basket_id=basket_id,
            owner_model_key=owner_model_key,
            owner_record_id=owner_record_id,
            currency=currency,
            items=items,
            source_basket_id=source_basket_id,
        )
        if revision < 1 or state not in ("editable", "frozen"):
            raise SalesError("Повреждено состояние корзины.")
        result.revision = revision
        result.state = state
        return result

    @staticmethod
    def _validate(currency: str, items: tuple[BasketItem, ...]) -> None:
        """Проверяет валюту, лимит строк и уникальность идентификаторов."""
        if currency not in ("USD", "EUR", "UAH"):
            raise SalesError("В CRM доступны USD, EUR и UAH.")
        if len(items) > 200 or len({i.id for i in items}) != len(items):
            raise SalesError("Повторные ID или более 200 позиций.")

    def replace_items(
        self, *, currency: str, items: tuple[BasketItem, ...], expected_revision: int
    ) -> None:
        """Атомарно принимает полностью проверенный новый состав."""
        if self.state != "editable":
            raise SalesConflictError("Корзина доступна только для чтения.")
        if expected_revision != self.revision:
            raise SalesConflictError("Корзина изменена. Сверьте актуальные данные.")
        self._validate(currency, items)
        if (currency, items) == (self.currency, self.items):
            return
        self.currency = currency
        self.items = items
        self.revision += 1

    def freeze(self) -> None:
        """Запрещает последующее коммерческое редактирование."""
        if self.state != "frozen":
            self.state = "frozen"
            self.revision += 1

    @property
    def total(self) -> Decimal:
        """Возвращает сумму округлённых строк, без второго итога владельца."""
        with localcontext() as context:
            context.prec = 40
            return sum((i.total for i in self.items), Decimal("0.00"))
