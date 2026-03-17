from uuid import UUID

from pydantic import BaseModel


class ResolveTenantResponseSchema(BaseModel):
    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None
