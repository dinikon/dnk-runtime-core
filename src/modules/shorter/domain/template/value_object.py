from enum import StrEnum

from src.modules.shared import EntityIdVO


class TemplateIdVO(EntityIdVO): ...


class TemplateTargetModuleTypeVO(StrEnum):
    SHORTER = "shorter"


class TemplateEntityTypeVO(StrEnum):
    REDIRECT = "redirect"
