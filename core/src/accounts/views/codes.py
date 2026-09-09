"""Code login entry points and ownership checks at confirmation."""

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.http import Http404
from django.http import HttpResponseRedirect
from allauth.account.views import ConfirmLoginCodeView as AllauthConfirmLoginCodeView
from allauth.account.views import RequestLoginCodeView as AllauthRequestLoginCodeView
from accounts.services.login_contacts import lock_code_owner
from accounts.services.phone_flows import PhoneLoginCodeProcess
from accounts.services.phones import login_phones
from accounts.models import User


class RequestLoginCodeView(AllauthRequestLoginCodeView):
    """Issue allauth codes only through an explicitly enabled delivery channel."""

    def dispatch(self, request, *args, **kwargs):
        """Reject disabled channels instead of silently sending through another one."""
        channel = (
            request.POST.get("channel")
            if request.method == "POST"
            else request.GET.get("channel", "email")
        )
        if (
            channel not in {None, "email", "telegram"}
            or (channel == "email" and not settings.EMAIL_CODE_LOGIN_ENABLED)
            or (channel == "telegram" and not settings.PHONE_LOGIN_ENABLED)
            or (
                not settings.EMAIL_CODE_LOGIN_ENABLED
                and not settings.PHONE_LOGIN_ENABLED
            )
        ):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass request-scoped channel and form arguments to the native form."""
        kwargs = super().get_form_kwargs()
        kwargs["channel"] = (
            self.request.POST.get("channel")
            if self.request.method == "POST"
            else self.request.GET.get("channel", "email")
        )
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        """Lock the selected contact while creating its UUID-bound code flow."""
        contact = getattr(form, "phone_contact", None)
        if contact is not None:
            user = User.objects.select_for_update().get(pk=contact.user_id)
            contact = login_phones(user).filter(pk=contact.pk).first()
            if contact is not None:
                PhoneLoginCodeProcess.initiate_for_contact(self.request, contact)
                return HttpResponseRedirect(self.get_success_url())
            form._user = None
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Build presentation context while preserving bound fields and validation errors."""
        context = super().get_context_data(**kwargs)
        channel = self.request.POST.get("channel") or self.request.GET.get("channel")
        context["code_channel"] = (
            "telegram"
            if channel == "telegram" and settings.PHONE_LOGIN_ENABLED
            else "email"
        )
        return context


class ConfirmLoginCodeView(AllauthConfirmLoginCodeView):
    """Finish code login only while the active user still owns the contact."""

    @transaction.atomic
    def form_valid(self, form):
        """Apply the validated action while preserving native allauth flow semantics."""
        process = self._process
        staged_user = process.user
        if (process.state.get("email") and not settings.EMAIL_CODE_LOGIN_ENABLED) or (
            process.state.get("phone") and not settings.PHONE_LOGIN_ENABLED
        ):
            process.abort()
            return redirect("account_login")
        if (
            staged_user is None
            and not process.state.get("user_id")
            and self._action == "resend"
        ):
            return super().form_valid(form)
        # A code proves access to the contact at issuance, not continued account
        # ownership. Lock and recheck before allauth verifies it or resends it.
        user = lock_code_owner(process)
        if user is None:
            process.abort()
            messages.error(
                self.request,
                "Не удалось подтвердить вход. Запросите новый код "
                "или выберите другой способ входа.",
            )
            return redirect("account_request_login_code")
        process._user = user
        process.stage.login.user = user
        if process.state.get("phone"):
            self._process = PhoneLoginCodeProcess(process.stage)
            self._process._user = user
        return super().form_valid(form)
