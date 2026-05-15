import enum


class TemplateVersionStatusVO(str, enum.Enum):
    """Value object статуса template version."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
