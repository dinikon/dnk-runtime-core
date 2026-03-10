from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.crm.domain.company.entity import CompanyEntity
    from src.modules.crm.domain.contact.entity import ContactEntity
    from src.modules.crm.domain.deal.entity import DealEntity


@dataclass(frozen=True, slots=True)
class LeadConversionResultVO:
    contact: ContactEntity | None
    company: CompanyEntity | None
    deal: DealEntity | None


__all__ = ["LeadConversionResultVO"]
