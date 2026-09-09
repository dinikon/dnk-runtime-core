"""Enforce feature switches before direct account endpoints execute."""

import json
from django.conf import settings
from django.contrib import messages
from django.urls import Resolver404, resolve
from django.http import Http404
from django.shortcuts import redirect
from allauth.account.internal.stagekit import clear_login
from .capabilities import enabled_providers, passkey_signup_enabled


def enforce_feature_access(request):
    """Block disabled entry points while retaining enrolled MFA and password reauth."""
    if not request.path.startswith("/accounts/"):
        return
    for provider, prefix in (
        ("google", "/accounts/google/"),
        ("github", "/accounts/github/"),
        ("telegram", "/accounts/oidc/telegram/"),
    ):
        if request.path.startswith(prefix) and provider not in enabled_providers():
            raise Http404()
    name = request.resolver_match.url_name if request.resolver_match else None
    if name == "socialaccount_signup":
        social = request.session.get("socialaccount_sociallogin") or {}
        provider = (social.get("account") or {}).get("provider")
        if provider and provider not in enabled_providers():
            request.session.pop("socialaccount_sociallogin", None)
            return redirect("account_login")
    if name in {
        "account_reauthenticate",
        "mfa_reauthenticate",
        "mfa_reauthenticate_webauthn",
        "core_email_reauthenticate",
    }:
        if not pending_action_enabled(request):
            request.session.pop("account_reauthentication_state", None)
            request.session.pop("core_email_reauthentication", None)
            messages.error(
                request, "Этот способ входа или действие отключены в настройках."
            )
            return redirect("core_account_overview")
    if name in {
        "account_confirm_login_code",
        "account_email_verification_sent",
        "account_confirm_email",
        "account_verify_phone",
        "mfa_authenticate",
        "mfa_trust",
        "mfa_signup_webauthn",
    }:
        if not pending_primary_enabled(request):
            clear_login(request)
            return redirect("account_login")
    blocked = (
        (
            name in {"account_signup", "socialaccount_signup"}
            and not settings.AUTH_SIGNUP_ENABLED
        )
        or (
            name in {"account_signup_by_passkey", "mfa_signup_webauthn"}
            and not passkey_signup_enabled()
        )
        or (name == "mfa_add_webauthn" and not settings.MFA_PASSKEY_ENROLLMENT_ENABLED)
        or (name == "mfa_activate_totp" and not settings.MFA_TOTP_ENROLLMENT_ENABLED)
        or (name == "mfa_login_webauthn" and not settings.MFA_PASSKEY_LOGIN_ENABLED)
        or (
            name in {"account_change_phone", "account_verify_phone"}
            and not settings.PHONE_LOGIN_ENABLED
        )
    )
    if blocked:
        if name == "mfa_signup_webauthn":
            clear_login(request)
        raise Http404()


def pending_primary_enabled(request):
    """Recheck the initiating method before a saved login can finish another stage."""
    from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
    from allauth.account.internal.stagekit import LOGIN_SESSION_KEY
    from .capabilities import password_login_enabled

    login = request.session.get(LOGIN_SESSION_KEY)
    if request.user.is_authenticated or not isinstance(login, dict):
        return True
    social = (login.get("signal_kwargs") or {}).get("sociallogin")
    if isinstance(social, dict):
        provider = (social.get("account") or {}).get("provider")
        if provider and provider not in enabled_providers():
            return False
    if login.get("signup"):
        # Closing registration does not invalidate the confirmation of a user
        # already created; a social provider switch still invalidates its proof.
        return True
    code_state = (
        login.get("state", {})
        .get("stages", {})
        .get("login_by_code", {})
        .get("data", {})
    )
    if code_state.get("phone"):
        return settings.PHONE_LOGIN_ENABLED
    if code_state.get("email"):
        return settings.EMAIL_CODE_LOGIN_ENABLED
    for record in reversed(request.session.get(AUTHENTICATION_METHODS_SESSION_KEY, [])):
        if record.get("reauthenticated"):
            continue
        method = record.get("method")
        if method == "password":
            return password_login_enabled()
        if method == "socialaccount":
            return record.get("provider") in enabled_providers()
        if method == "code":
            return (
                settings.PHONE_LOGIN_ENABLED
                if record.get("phone")
                else settings.EMAIL_CODE_LOGIN_ENABLED
            )
        if method == "mfa" and record.get("passwordless"):
            return settings.MFA_PASSKEY_LOGIN_ENABLED
    return True


def pending_action_enabled(request):
    """Prevent native reauth resume from executing a now-disabled suspended action.

    allauth calls the resolved view directly while resuming a POST, bypassing
    middleware. Inspect its server-held destination before the reauth succeeds.
    """
    from copy import copy

    state = request.session.get("account_reauthentication_state") or {}
    if (
        state.get("callback")
        == "allauth.socialaccount.internal.flows.connect.resume_connect"
    ):
        provider = ((state.get("state") or {}).get("account") or {}).get("provider")
        return provider in enabled_providers()
    if "request" in state:
        try:
            saved = json.loads(state["request"])
            preview = copy(request)
            preview.path = saved["path"]
            preview.resolver_match = resolve(preview.path)
            # Only the target route is needed; do not deserialize over the real
            # request or recursively inspect its current reauthentication URL.
            if preview.resolver_match.url_name in {
                "account_reauthenticate",
                "mfa_reauthenticate",
                "mfa_reauthenticate_webauthn",
                "core_email_reauthenticate",
            }:
                return True
            return enforce_feature_access(preview) is None
        except (Http404, Resolver404, KeyError, TypeError, ValueError):
            return False
    return True
