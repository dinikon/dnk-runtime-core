from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

from allauth.account.internal.flows.reauthentication import suspend_request
from allauth.account.internal.stagekit import clear_login

from .exceptions import PhoneConflictError
from .services.reauthentication import (
    recently_authenticated,
    uses_email_reauthentication,
)
from .services.feature_access import enforce_feature_access


class SocialOnlyReauthenticationMiddleware(MiddlewareMixin):
    """Close allauth's no-local-method exception for sensitive account actions."""

    exempt_views = {
        "account_logout",
        "core_email_reauthenticate",
        "account_reauthenticate",
        "mfa_reauthenticate",
        "mfa_reauthenticate_webauthn",
    }
    sensitive_get_views = {
        "mfa_add_webauthn",
        "mfa_activate_totp",
        "mfa_view_recovery_codes",
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Apply feature switches and require fresh authentication for sensitive actions."""
        response = enforce_feature_access(request)
        if response is not None:
            return response
        name = request.resolver_match.url_name if request.resolver_match else None
        if (
            not name
            or not request.path.startswith("/accounts/")
            or name in self.exempt_views
        ):
            return None
        if (
            request.method in {"GET", "HEAD", "OPTIONS"}
            and name not in self.sensitive_get_views
        ):
            return None
        if uses_email_reauthentication(request.user) and not recently_authenticated(
            request
        ):
            return suspend_request(request, reverse("core_email_reauthenticate"))
        return None

    def process_response(self, request, response):
        """Prevent account pages and form responses from being cached."""
        if request.path.startswith("/accounts/"):
            add_never_cache_headers(response)
        return response

    def process_exception(self, request, exception):
        """Recover from a concurrent phone claim without exposing its current owner."""
        if not isinstance(exception, PhoneConflictError):
            return None
        clear_login(request)
        request.session.pop("account_phone_verification", None)
        messages.error(
            request,
            "Не удалось подключить номер. Повторите с другим номером "
            "или выберите другой способ входа.",
        )
        return redirect(
            "account_change_phone"
            if request.user.is_authenticated
            else "account_signup"
        )
