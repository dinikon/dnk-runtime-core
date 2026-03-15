from src.modules.shared.domain.errors import DomainError


class ContactPointNotFoundError(DomainError):
    def __init__(self, point_id: str):
        super().__init__(f"Contact point not found: {point_id}")


class ContactNotFoundError(DomainError):
    def __init__(self, contact_id: str):
        super().__init__(f"Contact not found: {contact_id}")


class ContactPointKindNotSupportedError(DomainError):
    def __init__(self, kind: str):
        super().__init__(f"Unsupported contact point kind: {kind}")


class ContactPointValueRequiredError(DomainError):
    def __init__(self):
        super().__init__("Contact point value cannot be empty")


class ContactPointTypeCodeRequiredError(DomainError):
    def __init__(self):
        super().__init__("Contact point type code cannot be empty")


class ContactPointTypeTitleRequiredError(DomainError):
    def __init__(self):
        super().__init__("Contact point type title cannot be empty")


class ContactPointTypeAlreadyExistsError(DomainError):
    def __init__(self, kind: str, code: str):
        super().__init__(f"Contact point type already exists: kind={kind}, code={code}")


class ContactPointTypeNotFoundError(DomainError):
    def __init__(self, kind: str, code: str):
        super().__init__(f"Contact point type not found: kind={kind}, code={code}")


class ContactPointTypeInactiveError(DomainError):
    def __init__(self, kind: str, code: str):
        super().__init__(f"Contact point type is inactive: kind={kind}, code={code}")


class ContactPointTypeSystemLockedError(DomainError):
    def __init__(self, kind: str, code: str):
        super().__init__(
            f"System contact point type cannot be modified: kind={kind}, code={code}"
        )


class CompanyNameRequiredError(DomainError):
    def __init__(self):
        super().__init__("company_name cannot be empty")


class LeadTitleRequiredError(DomainError):
    def __init__(self):
        super().__init__("title cannot be empty")


class LeadPersonNameRequiredForConversionError(DomainError):
    def __init__(self):
        super().__init__("person_name is required to convert lead to contact")


class LeadCompanyNameRequiredForConversionError(DomainError):
    def __init__(self):
        super().__init__("company_name is required to convert lead to company")


class DealTitleRequiredError(DomainError):
    def __init__(self):
        super().__init__("deal title cannot be empty")


class ProductRowNotFoundError(DomainError):
    def __init__(self, row_id: str):
        super().__init__(f"Product row not found: {row_id}")


class ProductRowEntityIdRequiredError(DomainError):
    def __init__(self):
        super().__init__("entity_id must be greater than zero")


class ProductRowProductNameRequiredError(DomainError):
    def __init__(self):
        super().__init__("product_name cannot be empty")


class ProductRowMeasureCodeRequiredError(DomainError):
    def __init__(self):
        super().__init__("measure_code cannot be empty")


class ProductRowMeasureNameRequiredError(DomainError):
    def __init__(self):
        super().__init__("measure_name cannot be empty")


class ProductRowQuantityMustBePositiveError(DomainError):
    def __init__(self):
        super().__init__("quantity must be greater than zero")


class ProductRowFieldMustBeNonNegativeError(DomainError):
    def __init__(self, field_name: str):
        super().__init__(f"{field_name} must be non-negative")


class ProductRowDiscountTypeNotSupportedError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Unsupported discount type: {value}")


__all__ = [
    "CompanyNameRequiredError",
    "DealTitleRequiredError",
    "ProductRowDiscountTypeNotSupportedError",
    "ProductRowEntityIdRequiredError",
    "ProductRowFieldMustBeNonNegativeError",
    "ProductRowMeasureCodeRequiredError",
    "ProductRowMeasureNameRequiredError",
    "ProductRowNotFoundError",
    "ProductRowProductNameRequiredError",
    "ProductRowQuantityMustBePositiveError",
    "ContactPointKindNotSupportedError",
    "ContactNotFoundError",
    "ContactPointNotFoundError",
    "ContactPointTypeAlreadyExistsError",
    "ContactPointTypeCodeRequiredError",
    "ContactPointTypeInactiveError",
    "ContactPointTypeNotFoundError",
    "ContactPointTypeSystemLockedError",
    "ContactPointTypeTitleRequiredError",
    "ContactPointValueRequiredError",
    "LeadCompanyNameRequiredForConversionError",
    "LeadPersonNameRequiredForConversionError",
    "LeadTitleRequiredError",
]
