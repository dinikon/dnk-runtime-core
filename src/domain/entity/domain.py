from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.value_object.tenant_api_auth_mode import TenantApiAuthMode
from domain.value_object.tenant_domain_kind import TenantDomainKind
from domain.value_object.tenant_domain_tls_mode import TenantDomainTlsMode
from domain.value_object.tenant_domain_verification_status import (
    TenantDomainVerificationStatus,
)
from domain.value_object.tenant_domian_status import TenantDomainStatus
from domain.value_object.tenant_service_type import TenantServiceType


@dataclass(slots=True)
class TenantDomain:
    id: str
    tenant_id: str
    service_type: TenantServiceType
    kind: TenantDomainKind
    host: str
    base_path: str | None
    auth_mode: TenantApiAuthMode | None
    status: TenantDomainStatus
    is_primary: bool
    is_wildcard: bool
    parent_domain: str | None
    verification_status: TenantDomainVerificationStatus
    tls_mode: TenantDomainTlsMode
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
