from src.modules.crm.domain.company import CompanyEntity, CompanyIdVO
from src.modules.crm.domain.contact import ContactEntity, ContactIdVO
from src.modules.crm.domain.contact_point import (
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointKindVO,
    ContactPointTypeCodeVO,
    ContactPointTypeDictionaryEntity,
    ContactPointTypeVO,
)
from src.modules.crm.domain.deal import DealEntity, DealIdVO, DealTitleVO
from src.modules.crm.domain.lead import (
    LeadConversionModeVO,
    LeadConversionResultVO,
    LeadEntity,
    LeadIdVO,
    LeadTitleVO,
)
from src.modules.crm.domain.shared import CompanyNameVO, CrmEntityIdVO, PersonNameVO

__all__ = [
    "CompanyEntity",
    "CompanyIdVO",
    "CompanyNameVO",
    "ContactEntity",
    "ContactIdVO",
    "PersonNameVO",
    "ContactPointEntity",
    "ContactPointIdVO",
    "ContactPointKindVO",
    "ContactPointTypeVO",
    "ContactPointTypeCodeVO",
    "ContactPointTypeDictionaryEntity",
    "CrmEntityIdVO",
    "DealEntity",
    "DealIdVO",
    "DealTitleVO",
    "LeadEntity",
    "LeadConversionModeVO",
    "LeadConversionResultVO",
    "LeadIdVO",
    "LeadTitleVO",
]
