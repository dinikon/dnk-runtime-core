from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateTenantCommand:
    """Команда создания tenant, primary domain и tenant admin пользователя."""

    tenant_name: str
    external_id: str
    tenant_domain_host: str
    user_last_name: str
    user_first_name: str
    user_email: str


__all__ = ["CreateTenantCommand"]
