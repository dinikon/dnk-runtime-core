"""Small, same-origin JSON endpoints backed by Django sessions and policy."""

from accounts.services.capabilities import public_capabilities
from accounts.presentation.navigation import show_admin_link
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def session(request):
    """Return authentication state and a CSRF token without requiring login."""
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "csrfToken": get_token(request),
            "showAdminLink": show_admin_link(request.user),
        }
    )


@require_GET
@never_cache
def me(request):
    """Expose the current user's public profile, or a JSON 401 for guests."""
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    return JsonResponse(
        {
            "id": str(user.pk),
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )


@require_GET
@never_cache
def capabilities(request):
    """Publish enabled entry points without credentials or account-specific data."""
    return JsonResponse(public_capabilities())
