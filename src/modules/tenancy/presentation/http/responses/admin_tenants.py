from uuid import UUID

from pydantic import BaseModel


class AdminCreateTenantResponseSchema(BaseModel):
    """Pydantic-схема ответа admin endpoint создания tenant."""

    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str
