from src.modules.shared.domain.identity_context import RequestContext

WRITE_PERMISSIONS = (
    "currency.manage_enabled",
    "currency.manage_policy",
    "currency.manage_rates",
    "currency.change_functional_currency",
    "currency.import_rates",
)


def permissions(context: RequestContext) -> list[str]:
    """Compute capabilities from the authenticated principal, without HTTP handling."""
    principal = context.principal
    if principal is None or not principal.is_authenticated or not principal.tenant_id:
        return []
    if "admin" in principal.roles:
        return ["currency.view", *WRITE_PERMISSIONS]
    return ["currency.view"] if "member" in principal.roles else []


__all__ = ["permissions"]
