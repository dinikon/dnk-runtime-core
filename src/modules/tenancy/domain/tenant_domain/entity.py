from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import uuid6

from src.modules.shared import EntityIdVO
from src.modules.tenancy.domain.tenant_domain.error import (
    InvalidTenantDomainHostError,
)
from src.modules.tenancy.domain.tenant_domain.value_object import (
    TenantDomainIdVO,
    TenantDomainKind,
    TenantDomainStatus,
    TenantDomainTlsMode,
    TenantDomainVerificationStatus,
    TenantServiceType,
)

@dataclass(slots=True)
class TenantDomain:
    """Доменная сущность host/domain, связанного с tenant."""

    id: TenantDomainIdVO
    tenant_id: EntityIdVO
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
    def create_primary_console_domain(
        cls,
        tenant_id: EntityIdVO,
        host: str,
    ) -> "TenantDomain":
        """Создает primary console domain tenant с verified/active статусами."""
        normalized_host = host.strip().lower()
        if not normalized_host:
            raise InvalidTenantDomainHostError()

        now = datetime.now(UTC)
        return cls(
            id=TenantDomainIdVO.from_value(uuid6.uuid7()),
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


__all__ = ["TenantDomain"]
