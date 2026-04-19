from __future__ import annotations

from uuid import UUID

from src.modules.tenancy.domain.tenant_domain import (
    TenantDomain,
    TenantDomainKind,
    TenantDomainStatus,
    TenantDomainTlsMode,
    TenantDomainVerificationStatus,
    TenantServiceType,
)
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


def tenant_domain_to_model(domain: TenantDomain) -> TenantDomainModel:
    """Мапит доменную TenantDomain entity в SQLAlchemy TenantDomainModel."""
    return TenantDomainModel(
        id=domain.id,
        tenant_id=domain.tenant_id,
        service_type=domain.service_type,
        kind=domain.kind,
        host=domain.host,
        base_path=domain.base_path,
        auth_mode=domain.auth_mode,
        status=domain.status,
        is_primary=domain.is_primary,
        is_wildcard=domain.is_wildcard,
        parent_domain=domain.parent_domain,
        verification_status=domain.verification_status,
        tls_mode=domain.tls_mode,
        metadata_json=domain.metadata_json,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def tenant_domain_model_to_entity(model: TenantDomainModel) -> TenantDomain:
    """Мапит SQLAlchemy TenantDomainModel в доменную TenantDomain entity."""
    return TenantDomain(
        id=_to_uuid(model.id),
        tenant_id=_to_uuid(model.tenant_id),
        service_type=TenantServiceType(model.service_type),
        kind=TenantDomainKind(model.kind),
        host=model.host,
        base_path=model.base_path,
        auth_mode=model.auth_mode,
        status=TenantDomainStatus(model.status),
        is_primary=model.is_primary,
        is_wildcard=model.is_wildcard,
        parent_domain=model.parent_domain,
        verification_status=TenantDomainVerificationStatus(model.verification_status),
        tls_mode=TenantDomainTlsMode(model.tls_mode),
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_uuid(value: UUID | str) -> UUID:
    """Приводит UUID или строку из ORM к UUID."""
    if isinstance(value, UUID):
        return value
    return UUID(value)


__all__ = [
    "tenant_domain_model_to_entity",
    "tenant_domain_to_model",
]
