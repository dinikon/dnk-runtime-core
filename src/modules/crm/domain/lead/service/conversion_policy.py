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

    @staticmethod
    def relations(
        *,
        links: tuple[tuple[EntityIdVO | None, EntityIdVO | None], ...],
        new_contact: EntityIdVO | None,
        new_company: EntityIdVO | None,
        source_contact: EntityIdVO | None,
        source_company: EntityIdVO | None,
        additional_companies: tuple[EntityIdVO, ...],
    ) -> frozenset[tuple[EntityIdVO, EntityIdVO]]:
        """Планирует только разрешённые связи, включающие создаваемую сторону."""
        pairs = set()
        if new_contact and new_company:
            pairs.add((new_contact, new_company))
        allowed_companies = set(additional_companies) | (
            {source_company} if source_company else set()
        )
        for contact, company in links:
            contact = contact or new_contact
            company = company or new_company
            if (
                contact is None
                or company is None
                or (contact != new_contact and company != new_company)
            ):
                raise SalesError(
                    "Связь должна включать хотя бы один создаваемый объект."
                )
            if contact != new_contact and contact != source_contact:
                raise SalesError("Недопустимый контакт связи.")
            if company != new_company and company not in allowed_companies:
                raise SalesError("Недопустимая компания связи.")
            pairs.add((contact, company))
        return frozenset(pairs)

    @staticmethod
    def deal_participants(
        *,
        new_contact: EntityIdVO | None,
        new_company: EntityIdVO | None,
        source_contact: EntityIdVO | None,
        source_company: EntityIdVO | None,
        additional_companies: tuple[EntityIdVO, ...],
    ) -> tuple[tuple[EntityIdVO, ...], tuple[EntityIdVO, ...]]:
        """Включает исходные и создаваемые записи без дубликатов участников."""
        contacts = {
            value for value in (new_contact, source_contact) if value is not None
        }
        companies = set(additional_companies) | {
            value for value in (new_company, source_company) if value is not None
        }
        return tuple(sorted(contacts, key=str)), tuple(sorted(companies, key=str))
