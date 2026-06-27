from src.modules.shared import DomainError


class CompanyNotFoundError(DomainError):
    """Доменная ошибка отсутствующей CRM-компании."""

    def __init__(self, company_id: str):
        """Формирует сообщение с id отсутствующей компании."""
        super().__init__(f"Company {company_id} not found")


class InvalidCompanyLegalNameError(DomainError):
    """Доменная ошибка некорректного юридического названия компании."""

    def __init__(self):
        """Формирует сообщение об обязательном юридическом названии компании."""
        super().__init__("Company legal name must not be empty.")


__all__ = [
    "CompanyNotFoundError",
    "InvalidCompanyLegalNameError",
]
