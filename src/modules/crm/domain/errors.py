from __future__ import annotations

from uuid import UUID

from src.modules.shared.domain.errors import DomainError


class InvalidContactFirstNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Contact first_name is invalid: '{value}'.")


class InvalidContactLastNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Contact last_name is invalid: '{value}'.")


class InvalidContactMiddleNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Contact middle_name is invalid: '{value}'.")


class InvalidCompanyNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Company company_name is invalid: '{value}'.")


class InvalidCompanyLastNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Company last_name is invalid: '{value}'.")


class ContactNotFoundError(DomainError):
    def __init__(self, contact_id: UUID):
        super().__init__(f"Contact '{contact_id}' was not found.")


class CompanyNotFoundError(DomainError):
    def __init__(self, company_id: UUID):
        super().__init__(f"Company '{company_id}' was not found.")


__all__ = [
    "CompanyNotFoundError",
    "ContactNotFoundError",
    "InvalidCompanyLastNameError",
    "InvalidCompanyNameError",
    "InvalidContactFirstNameError",
    "InvalidContactLastNameError",
    "InvalidContactMiddleNameError",
]
