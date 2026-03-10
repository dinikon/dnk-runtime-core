from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.crm.domain.company.entity import Company
    from src.modules.crm.domain.contact.entity import Contact
    from src.modules.crm.domain.deal.entity import Deal


@dataclass(frozen=True, slots=True)
class LeadConversionResult:
    contact: Contact | None
    company: Company | None
    deal: Deal | None


__all__ = ["LeadConversionResult"]

