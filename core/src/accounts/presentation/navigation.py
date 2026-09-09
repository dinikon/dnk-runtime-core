"""Role-aware navigation hints; Django admin still enforces its own permissions."""


def show_admin_link(user) -> bool:
    """Offer the admin entry point to active staff and superusers only."""
    return bool(
        user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )
