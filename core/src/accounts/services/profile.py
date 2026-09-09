"""Persist personal names without modifying identity or authentication state."""


def update_profile(user, *, first_name, last_name, middle_name=""):
    """Save validated name fields only, preserving concurrent security changes."""
    user.first_name = first_name
    user.last_name = last_name
    user.middle_name = middle_name
    user.save(update_fields=["first_name", "last_name", "middle_name"])
