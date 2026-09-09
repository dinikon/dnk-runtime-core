"""Bounded allauth WebAuthn view extensions requiring owner verification."""

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic.edit import FormView
from allauth.account.adapter import get_adapter
from allauth.account.models import Login
from allauth.account.utils import get_next_redirect_url
from allauth.mfa.webauthn.internal import auth, flows
from allauth.mfa.webauthn.views import (
    AddWebAuthnView,
    LoginWebAuthnView,
    SignupWebAuthnView,
    RemoveWebAuthnView,
)
from allauth.mfa.base.internal.flows import post_authentication
from allauth.mfa.recovery_codes.internal.flows import auto_generate_recovery_codes
from fido2.webauthn import UserVerificationRequirement
from accounts.models import User
from accounts.services.capabilities import require_primary_login


class AddPasskeyView(AddWebAuthnView):
    """Create only discoverable passkeys that require device owner verification."""

    def get_context_data(self, **kwargs):
        # Calling AddWebAuthnView here would generate a non-UV challenge first.
        """Build presentation context while preserving bound fields and validation errors."""
        context = FormView.get_context_data(self, **kwargs)
        context["js_data"] = {
            "creation_options": auth.begin_registration(self.request.user, True),
        }
        return context


class LoginPasskeyView(LoginWebAuthnView):
    """Require verified device ownership before completing passwordless login."""

    def get(self, request, *args, **kwargs):
        """Return the request options for a verified-owner passwordless assertion."""
        if not get_adapter().is_ajax(request):
            return HttpResponseRedirect(reverse("account_login"))
        options, state = auth.get_server().authenticate_begin(
            credentials=[],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        auth.set_state(state)
        return JsonResponse({"request_options": dict(options)})

    def form_valid(self, form):
        """Apply the validated action while preserving native allauth flow semantics."""
        authenticator = form.cleaned_data["credential"]
        # allauth validates next against the current host and HTTPS requirement.
        login = Login(
            user=authenticator.user,
            redirect_url=get_next_redirect_url(self.request),
        )
        return flows.perform_passwordless_login(self.request, authenticator, login)


class SignupPasskeyView(SignupWebAuthnView):
    """Finish native passkey signup and show freshly generated recovery codes."""

    def get_context_data(self, **kwargs):
        """Build presentation context while preserving bound fields and validation errors."""
        context = super().get_context_data(**kwargs)
        # Upstream drops the bound form when building a fresh challenge.
        if "form" in kwargs:
            context["form"] = kwargs["form"]
        return context

    @transaction.atomic
    def form_valid(self, form):
        """Apply the validated action while preserving native allauth flow semantics."""
        stage = self._login_stage
        authenticator = flows.signup_authenticator(
            self.request,
            user=stage.login.user,
            name=form.cleaned_data["name"],
            credential=form.cleaned_data["credential"],
        )
        post_authentication(self.request, authenticator, passwordless=True)
        response = stage.exit()
        if self.request.user.is_authenticated:
            auto_generate_recovery_codes(self.request)
            # Save only a host-validated redirect; never trust the posted next.
            target = stage.login.redirect_url or settings.LOGIN_REDIRECT_URL
            if not get_adapter().is_safe_url(target):
                target = settings.LOGIN_REDIRECT_URL
            self.request.session["core_passkey_signup_next"] = target
            return redirect("mfa_view_recovery_codes")
        return response


@login_required
@require_POST
def continue_passkey_signup(request):
    """Consume the saved safe redirect after recovery codes are displayed."""
    target = request.session.pop(
        "core_passkey_signup_next", settings.LOGIN_REDIRECT_URL
    )
    if not get_adapter().is_safe_url(target):
        target = settings.LOGIN_REDIRECT_URL
    return redirect(target)


class RemovePasskeyView(RemoveWebAuthnView):
    """Retain allauth removal semantics while protecting the last primary method."""

    @transaction.atomic
    def form_valid(self, form):
        """Serialize account removals and keep the final usable key when needed."""
        user = User.objects.select_for_update().get(pk=self.request.user.pk)
        authenticator = self.get_object()
        try:
            require_primary_login(user, exclude_passkey=authenticator.pk)
        except ValidationError as exc:
            messages.error(self.request, exc.messages[0])
            return redirect("mfa_list_webauthn")
        return super().form_valid(form)
