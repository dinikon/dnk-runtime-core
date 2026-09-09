"""Provider presentation, linking and signup hooks for allauth."""

from django.shortcuts import redirect
from allauth.account.internal.flows.reauthentication import stash_and_reauthenticate
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthProcess, Provider, ProviderAccount
from accounts.services import reauthentication
from accounts.services.capabilities import enabled_providers


class DisabledSocialProvider(Provider):
    """Display saved connections without enabling redirects or token login."""

    uses_apps = False
    account_class = ProviderAccount

    def __init__(self, request, provider):
        """Initialize the native component and apply CORE field or provider metadata."""
        super().__init__(request)
        self.id = provider
        self.name = {"google": "Google", "github": "GitHub", "telegram": "Telegram"}[
            provider
        ]


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Resolve provider availability and protect delayed social account linking."""

    def get_provider(self, request, provider, client_id=None):
        """Resolve an enabled provider or display a disabled saved connection."""
        if (
            provider in {"google", "github", "telegram"}
            and provider not in enabled_providers()
        ):
            return DisabledSocialProvider(request, provider)
        result = super().get_provider(request, provider, client_id=client_id)
        if getattr(result, "sub_id", None) == "telegram":
            from accounts.integrations.telegram_oidc import TelegramProvider

            result = TelegramProvider(request, app=result.app)
        return result

    def is_auto_signup_allowed(self, request, sociallogin):
        """Ask for missing profile names and retain Telegram's explicit signup step."""
        if sociallogin.account.provider == "telegram":
            return False
        if not all(
            0 < len(value.strip()) <= 150
            for value in (sociallogin.user.first_name, sociallogin.user.last_name)
        ):
            return False
        return super().is_auto_signup_allowed(request, sociallogin)

    def pre_social_login(self, request, sociallogin):
        """Recheck recent authentication when a delayed social linking flow returns."""
        super().pre_social_login(request, sociallogin)
        # OAuth may finish after the recent-auth window used to start a connect.
        # Native allauth skips this check for users with no local reauth method.
        if (
            sociallogin.state.get("process") == AuthProcess.CONNECT
            and reauthentication.uses_email_reauthentication(request.user)
            and not reauthentication.recently_authenticated(request)
        ):
            stash_and_reauthenticate(
                request,
                sociallogin.serialize(),
                "allauth.socialaccount.internal.flows.connect.resume_connect",
            )
            raise ImmediateHttpResponse(redirect("core_email_reauthenticate"))
