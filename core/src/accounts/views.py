import logging
import smtplib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic.edit import FormView

from allauth.account.adapter import get_adapter
from allauth.account.decorators import reauthentication_required
from allauth.account.internal.flows.login import record_authentication
from allauth.account.internal.flows.reauthentication import resume_request
from allauth.account.mixins import NextRedirectMixin
from allauth.account.models import EmailAddress, Login
from allauth.account.utils import get_next_redirect_url
from allauth.account.views import ConfirmLoginCodeView as AllauthConfirmLoginCodeView
from allauth.account.views import RequestLoginCodeView as AllauthRequestLoginCodeView
from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled
from allauth.mfa.webauthn.internal import auth, flows
from allauth.mfa.webauthn.views import AddWebAuthnView, LoginWebAuthnView
from allauth.mfa.webauthn.views import SignupWebAuthnView
from allauth.mfa.base.internal.flows import post_authentication
from allauth.mfa.recovery_codes.internal.flows import auto_generate_recovery_codes
from allauth.socialaccount.models import SocialAccount
from allauth.core import ratelimit
from allauth.usersessions.internal.flows.sessions import end_sessions
from allauth.usersessions.models import UserSession
from fido2.webauthn import UserVerificationRequirement

from . import reauthentication
from .forms import EmailReauthenticationForm
from .models import User

logger = logging.getLogger(__name__)


class RequestLoginCodeView(AllauthRequestLoginCodeView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["channel"] = (
            self.request.POST.get("channel")
            if self.request.method == "POST"
            else self.request.GET.get("channel", "email")
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        channel = self.request.POST.get("channel") or self.request.GET.get("channel")
        context["code_channel"] = (
            "telegram"
            if channel == "telegram" and settings.PHONE_LOGIN_ENABLED
            else "email"
        )
        return context


class ConfirmLoginCodeView(AllauthConfirmLoginCodeView):
    @transaction.atomic
    def form_valid(self, form):
        process = self._process
        staged_user = process.user
        if (
            staged_user is None
            and not process.state.get("user_id")
            and self._action == "resend"
        ):
            return super().form_valid(form)
        # A code proves access to the contact at issuance, not continued account
        # ownership. Lock and recheck before allauth verifies it or resends it.
        user = (
            User.objects.select_for_update().filter(pk=staged_user.pk).first()
            if staged_user
            else None
        )
        phone = process.state.get("phone")
        email = process.state.get("email")
        owns_contact = bool(user and user.is_active)
        if owns_contact and phone:
            owns_contact = (
                settings.PHONE_LOGIN_ENABLED
                and user.phone_verified
                and user.phone == phone
            )
        elif owns_contact and email:
            owns_contact = bool(
                EmailAddress.objects.select_for_update()
                .filter(user=user, email__iexact=email)
                .first()
            )
        else:
            owns_contact = False
        if not owns_contact:
            process.abort()
            messages.error(
                self.request,
                "Не удалось подтвердить вход. Запросите новый код "
                "или выберите другой способ входа.",
            )
            return redirect("account_request_login_code")
        process._user = user
        process.stage.login.user = user
        return super().form_valid(form)


class EmailReauthenticationView(LoginRequiredMixin, NextRedirectMixin, FormView):
    template_name = "accounts/reauthenticate_email.html"
    form_class = EmailReauthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and not reauthentication.uses_email_reauthentication(request.user)
        ):
            methods = get_adapter().get_reauthentication_methods(request.user)
            if methods:
                return HttpResponseRedirect(methods[0]["url"])
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "verify")
        if action == "request":
            if not ratelimit.consume(request, action="core_email_reauthenticate"):
                return ratelimit.respond_429(request)
            email = reauthentication.verified_email(request.user)
            if not email:
                raise PermissionDenied(
                    "Подтвердите email перед изменением настроек безопасности."
                )
            adapter = get_adapter()
            code = adapter.generate_login_code()
            request.session.pop(reauthentication.STATE_KEY, None)
            try:
                adapter.send_mail(
                    "accounts/email/reauthenticate",
                    email.email,
                    {"request": request, "user": request.user, "code": code},
                )
            except (OSError, smtplib.SMTPException):
                logger.warning("Core email reauthentication delivery failed")
                messages.error(request, "Не удалось отправить код. Повторите позже.")
            else:
                request.session[reauthentication.STATE_KEY] = (
                    reauthentication.new_state(
                        request.user,
                        email.email,
                        code,
                    )
                )
            return self.render_to_response(
                self.get_context_data(form=self.form_class())
            )
        if action != "verify":
            return HttpResponseBadRequest()
        if not ratelimit.consume(request, action="reauthenticate"):
            return ratelimit.respond_429(request)
        form = self.get_form()
        state = reauthentication.get_state(request)
        form_valid = form.is_valid()
        valid = reauthentication.check_code(request, form.cleaned_data.get("code", ""))
        if form_valid and valid:
            record_authentication(
                request,
                request.user,
                method="code",
                email=state["email"],
                reauthenticated=True,
            )
            return resume_request(request) or redirect("core_account_overview")
        form.add_error(
            "code", "Код неверен или истек. Запросите новый код при необходимости."
        )
        return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state = reauthentication.get_state(self.request)
        email = reauthentication.verified_email(self.request.user)
        address = email.email if email else ""
        local, _, domain = address.partition("@")
        context.update(
            {
                "code_sent": bool(state),
                "masked_email": f"{local[:2]}***@{domain}" if address else "",
            }
        )
        return context


@login_required
@never_cache
def account_overview(request):
    return render(
        request,
        "accounts/overview.html",
        {
            "email_addresses": EmailAddress.objects.filter(user=request.user),
            "phone": request.user.phone,
            "phone_verified": request.user.phone_verified,
            "mfa_enabled": is_mfa_enabled(request.user),
            "passkey_count": Authenticator.objects.filter(
                user=request.user,
                type=Authenticator.Type.WEBAUTHN,
            ).count(),
            "social_accounts": SocialAccount.objects.filter(user=request.user),
            "sessions": UserSession.objects.purge_and_list(request.user),
        },
    )


@login_required
@require_POST
@reauthentication_required
def revoke_session(request, pk):
    session = get_object_or_404(UserSession, pk=pk, user=request.user)
    was_current = session.is_current()
    end_sessions(request, [session])
    if was_current:
        return redirect("/")
    messages.success(request, "Сессия завершена.")
    return redirect("usersessions_list")


class AddPasskeyView(AddWebAuthnView):
    def get_context_data(self, **kwargs):
        # Calling AddWebAuthnView here would generate a non-UV challenge first.
        context = FormView.get_context_data(self, **kwargs)
        context["js_data"] = {
            "creation_options": auth.begin_registration(self.request.user, True),
        }
        return context


class LoginPasskeyView(LoginWebAuthnView):
    def get(self, request, *args, **kwargs):
        if not get_adapter().is_ajax(request):
            return HttpResponseRedirect(reverse("account_login"))
        options, state = auth.get_server().authenticate_begin(
            credentials=[],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        auth.set_state(state)
        return JsonResponse({"request_options": dict(options)})

    def form_valid(self, form):
        authenticator = form.cleaned_data["credential"]
        # allauth validates next against the current host and HTTPS requirement.
        login = Login(
            user=authenticator.user,
            redirect_url=get_next_redirect_url(self.request),
        )
        return flows.perform_passwordless_login(self.request, authenticator, login)


class SignupPasskeyView(SignupWebAuthnView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Upstream drops the bound form when building a fresh challenge.
        if "form" in kwargs:
            context["form"] = kwargs["form"]
        return context

    @transaction.atomic
    def form_valid(self, form):
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
    target = request.session.pop(
        "core_passkey_signup_next", settings.LOGIN_REDIRECT_URL
    )
    if not get_adapter().is_safe_url(target):
        target = settings.LOGIN_REDIRECT_URL
    return redirect(target)
