from enum import StrEnum


class LeadConversionModeVO(StrEnum):
    CONTACT_ONLY = "contact_only"
    COMPANY_ONLY = "company_only"
    CONTACT_AND_COMPANY = "contact_and_company"
    DEAL_ONLY = "deal_only"
    DEAL_AND_CONTACT = "deal_and_contact"
    DEAL_AND_COMPANY = "deal_and_company"
    DEAL_AND_CONTACT_AND_COMPANY = "deal_and_contact_and_company"


__all__ = ["LeadConversionModeVO"]
