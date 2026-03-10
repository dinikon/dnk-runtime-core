from src.modules.shared.domain.errors import ValidationError


class ContactPointNotFoundError(ValidationError):
    def __init__(self, point_id: str):
        super().__init__(f"Contact point not found: {point_id}")


class ContactPointKindNotSupportedError(ValidationError):
    def __init__(self, kind: str):
        super().__init__(f"Unsupported contact point kind: {kind}")


class ContactPointValueRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Contact point value cannot be empty")


class ContactPointTypeCodeRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Contact point type code cannot be empty")


class ContactPointTypeTitleRequiredError(ValidationError):
    def __init__(self):
        super().__init__("Contact point type title cannot be empty")


class ContactPointTypeAlreadyExistsError(ValidationError):
    def __init__(self, kind: str, code: str):
        super().__init__(
            f"Contact point type already exists: kind={kind}, code={code}"
        )


class ContactPointTypeNotFoundError(ValidationError):
    def __init__(self, kind: str, code: str):
        super().__init__(f"Contact point type not found: kind={kind}, code={code}")


class ContactPointTypeInactiveError(ValidationError):
    def __init__(self, kind: str, code: str):
        super().__init__(f"Contact point type is inactive: kind={kind}, code={code}")


class ContactPointTypeSystemLockedError(ValidationError):
    def __init__(self, kind: str, code: str):
        super().__init__(
            f"System contact point type cannot be modified: kind={kind}, code={code}"
        )


class CompanyNameRequiredError(ValidationError):
    def __init__(self):
        super().__init__("company_name cannot be empty")


class LeadTitleRequiredError(ValidationError):
    def __init__(self):
        super().__init__("title cannot be empty")


class LeadPersonNameRequiredForConversionError(ValidationError):
    def __init__(self):
        super().__init__("person_name is required to convert lead to contact")


class LeadCompanyNameRequiredForConversionError(ValidationError):
    def __init__(self):
        super().__init__("company_name is required to convert lead to company")


class DealTitleRequiredError(ValidationError):
    def __init__(self):
        super().__init__("deal title cannot be empty")


__all__ = [
    "CompanyNameRequiredError",
    "DealTitleRequiredError",
    "ContactPointKindNotSupportedError",
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
