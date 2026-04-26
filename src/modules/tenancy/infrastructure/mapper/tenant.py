from __future__ import annotations

from src.modules.shared import EntityIdVO
from src.modules.tenancy.domain.tenant import Tenant, TenantStatus
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


def tenant_to_model(tenant: Tenant) -> TenantModel:
    """Мапит доменную Tenant entity в SQLAlchemy TenantModel."""

    return TenantModel(
        id=tenant.id.uuid,
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
        id=EntityIdVO.from_value(model.id),
        name=model.name,
        external_id=model.external_id,
        status=TenantStatus(model.status),
        custom_config=model.custom_config,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


__all__ = [
    "tenant_model_to_entity",
    "tenant_to_model",
]
