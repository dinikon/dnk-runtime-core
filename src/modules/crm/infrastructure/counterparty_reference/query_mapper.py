from src.modules.crm.application.counterparty_reference.dto import (
    CounterpartyModelKey,
    CounterpartyReferenceDTO,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel


class CounterpartyReferenceQueryMapper:
    """Собирает публичные имена контрагентов из типизированных моделей CRM."""

    @staticmethod
    def company(model: CompanyModel) -> CounterpartyReferenceDTO:
        """Показывает юридическое название компании."""
        return CounterpartyReferenceDTO(
            CounterpartyModelKey.COMPANY, model.id, model.legal_name
        )

    @staticmethod
    def contact(model: ContactModel) -> CounterpartyReferenceDTO:
        """Показывает ФИО в принятом CRM порядке: фамилия, имя, отчество."""
        return CounterpartyReferenceDTO(
            CounterpartyModelKey.CONTACT,
            model.id,
            " ".join(
                part
                for part in (model.last_name, model.first_name, model.middle_name)
                if part
            ),
        )
