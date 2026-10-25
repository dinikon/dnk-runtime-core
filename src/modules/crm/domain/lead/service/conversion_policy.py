from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesError

MODES = {
    "contact": frozenset({"contact"}),
    "company": frozenset({"company"}),
    "contact_company": frozenset({"contact", "company"}),
    "contact_deal": frozenset({"contact", "deal"}),
    "company_deal": frozenset({"company", "deal"}),
    "contact_company_deal": frozenset({"contact", "company", "deal"}),
    "deal": frozenset({"deal"}),
}


class LeadConversionPolicy:
    """Чистые правила состава результатов и принадлежности копируемых данных."""

    @staticmethod
    def validate(
        mode: str,
        provided: set[str],
        selections: dict[str, tuple[EntityIdVO, ...] | None],
        source_ids: set[EntityIdVO],
        selected_company_ids: tuple[EntityIdVO, ...],
        allowed_company_ids: set[EntityIdVO],
    ) -> frozenset[str]:
        """Отклоняет неизвестный режим, лишние блоки и чужие исходные ссылки."""
        selected = MODES.get(mode)
        if selected is None:
            raise SalesError("Выберите один из семи режимов конвертации.")
        if provided - selected:
            raise SalesError("Переданы данные не выбранного результата.")
        for kind, ids in selections.items():
            if kind in selected:
                if ids is None:
                    raise SalesError(f"Явно выберите точки связи: {kind}.")
                if len(set(ids)) != len(ids) or not set(ids).issubset(source_ids):
                    raise SalesError("Точка связи не принадлежит исходному лиду.")
            elif ids is not None:
                raise SalesError("Переданы точки связи не выбранного результата.")
        if not set(selected_company_ids).issubset(allowed_company_ids) or len(
            set(selected_company_ids)
        ) != len(selected_company_ids):
            raise SalesError("Выбрана недопустимая дополнительная компания.")
        return selected
