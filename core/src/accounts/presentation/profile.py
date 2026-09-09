"""Human-readable account labels shared with allauth templates and authenticators."""


def user_display(user):
    """Show profile names or email instead of the internal username."""
    return user.display_name
