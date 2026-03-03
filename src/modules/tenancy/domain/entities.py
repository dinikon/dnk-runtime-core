from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.shared.domain.errors import ValidationError
from src.modules.tenancy.domain.value_objects.tenant_domain_kind import (
    TenantDomainKind,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_tls_mode import (
    TenantDomainTlsMode,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_verification_status import (
    TenantDomainVerificationStatus,
)
from src.modules.tenancy.domain.value_objects.tenant_domian_status import (
    TenantDomainStatus,
)
from src.modules.tenancy.domain.value_objects.tenant_service_type import (
    TenantServiceType,
)
from src.modules.tenancy.domain.value_objects.tenant_status import TenantStatus


@dataclass(slots=True)
class Tenant:
    id: UUID
    name: str
    external_id: str
    status: TenantStatus
    custom_config: dict[str, object] | None
    created_at: datetime
    updated_at: datetime

    def allows_login(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def allows_read_business_data(self) -> bool:
        return self.status in {TenantStatus.ACTIVE, TenantStatus.FREEZE}

    def allows_write_business_data(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    @classmethod
    def create(cls, name: str, external_id: str) -> "Tenant":
        normalized_name = name.strip()
        normalized_external_id = external_id.strip()
        if not normalized_name:
            raise ValidationError("Tenant name must not be empty.")
        if not normalized_external_id:
            raise ValidationError("Tenant external_id must not be empty.")

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            name=normalized_name,
            external_id=normalized_external_id,
            status=TenantStatus.ACTIVE,
            custom_config=None,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class TenantDomain:
    id: UUID
    tenant_id: UUID
    service_type: TenantServiceType
    kind: TenantDomainKind
    host: str
    base_path: str | None
    auth_mode: str | None
    status: TenantDomainStatus
    is_primary: bool
    is_wildcard: bool
    parent_domain: str | None
    verification_status: TenantDomainVerificationStatus
    tls_mode: TenantDomainTlsMode
    metadata_json: dict[str, object] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_primary(cls, tenant_id: UUID, host: str) -> "TenantDomain":
        normalized_host = host.strip().lower()
        if not normalized_host:
            raise ValidationError("Tenant domain host must not be empty.")

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            service_type=TenantServiceType.CONSOLE,
            kind=TenantDomainKind.DEFAULT,
            host=normalized_host,
            base_path=None,
            auth_mode=None,
            status=TenantDomainStatus.ACTIVE,
            is_primary=True,
            is_wildcard=False,
            parent_domain=None,
            verification_status=TenantDomainVerificationStatus.VERIFIED,
            tls_mode=TenantDomainTlsMode.MANAGED,
            metadata_json=None,
            created_at=now,
            updated_at=now,
        )
