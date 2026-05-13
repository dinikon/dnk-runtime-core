import enum


class TemplateStatusVO(str, enum.Enum):
    """Value object статуса message template."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
