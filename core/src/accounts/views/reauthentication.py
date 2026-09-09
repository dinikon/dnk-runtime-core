"""HTTP orchestration for local email reauthentication."""

import logging
import smtplib
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic.edit import FormView
from allauth.account.adapter import get_adapter
from allauth.account.internal.flows.login import record_authentication
from allauth.account.internal.flows.reauthentication import resume_request
from allauth.account.mixins import NextRedirectMixin
from allauth.core import ratelimit
from accounts.services import reauthentication
from accounts.forms import EmailReauthenticationForm

logger = logging.getLogger(__name__)


class EmailReauthenticationView(LoginRequiredMixin, NextRedirectMixin, FormView):
    """Confirm sensitive actions by email for users without a local reauth method."""

    template_name = "accounts/reauthenticate_email.html"
    form_class = EmailReauthenticationForm

    def dispatch(self, request, *args, **kwargs):
        """Select the permitted reauthentication flow before handling form actions."""
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
        """Issue or verify an email proof and resume the exact suspended action."""
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
        """Build presentation context while preserving bound fields and validation errors."""
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
