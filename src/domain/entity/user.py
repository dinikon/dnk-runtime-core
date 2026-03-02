from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TenantUser:
    id: str
    tenant_id: str
    last_name: str
    first_name: str
    middle_name: str
    email: str
    avatar: str | None
    interface_language: str | None
    interface_theme: str | None
    timezone: str | None
    last_login_at: datetime | None
    last_login_ip: str | None
    last_active_at: datetime
    status: str
    initialized_at: datetime | None
    is_tenant_admin: bool
    created_at: datetime
    updated_at: datetime
