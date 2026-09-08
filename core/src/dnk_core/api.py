from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def session(request):
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "csrfToken": get_token(request),
        }
    )


@require_GET
@never_cache
def me(request):
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
