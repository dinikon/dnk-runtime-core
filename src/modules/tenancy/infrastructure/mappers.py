from __future__ import annotations

from uuid import UUID

from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.value_objects import (
    TenantDomainKind,
    TenantDomainStatus,
    TenantDomainTlsMode,
    TenantDomainVerificationStatus,
    TenantServiceType,
    TenantStatus,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


def tenant_to_model(tenant: Tenant) -> TenantModel:
    """Мапит доменную Tenant entity в SQLAlchemy TenantModel."""

    return TenantModel(
        id=tenant.id,
        name=tenant.name,
        external_id=tenant.external_id,
        status=tenant.status,
        custom_config=tenant.custom_config,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


def tenant_model_to_entity(model: TenantModel) -> Tenant:
    """Мапит SQLAlchemy TenantModel в доменную Tenant entity."""
    return Tenant(
        id=_to_uuid(model.id),
        name=model.name,
        external_id=model.external_id,
        status=TenantStatus(model.status),
        custom_config=model.custom_config,
        created_at=model.created_at,
        updated_at=model.updated_at,
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
    "tenant_model_to_entity",
    "tenant_to_model",
]
