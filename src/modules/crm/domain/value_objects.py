from __future__ import annotations

from src.modules.crm.domain.errors import (
    InvalidCompanyLastNameError,
    InvalidCompanyNameError,
    InvalidContactFirstNameError,
    InvalidContactLastNameError,
    InvalidContactMiddleNameError,
)

CRM_TEXT_MAX_LENGTH = 255


def normalize_contact_first_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > CRM_TEXT_MAX_LENGTH:
        raise InvalidContactFirstNameError(value)
    return normalized


def normalize_contact_last_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > CRM_TEXT_MAX_LENGTH:
        raise InvalidContactLastNameError(value)
    return normalized


def normalize_contact_middle_name(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > CRM_TEXT_MAX_LENGTH:
        raise InvalidContactMiddleNameError(value)
    return normalized


def normalize_company_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > CRM_TEXT_MAX_LENGTH:
        raise InvalidCompanyNameError(value)
    return normalized


def normalize_company_last_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > CRM_TEXT_MAX_LENGTH:
        raise InvalidCompanyLastNameError(value)
    return normalized


__all__ = [
    "CRM_TEXT_MAX_LENGTH",
    "normalize_company_last_name",
    "normalize_company_name",
    "normalize_contact_first_name",
    "normalize_contact_last_name",
    "normalize_contact_middle_name",
]
