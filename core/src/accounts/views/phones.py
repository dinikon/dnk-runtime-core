"""Owner-scoped phone management using Django forms and native allauth OTP checks."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, login_not_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from allauth.account.decorators import reauthentication_required
from allauth.decorators import rate_limit
from allauth.account.views import (
    _BaseVerifyPhoneView,
    _VerifyPhoneChangeView,
    _VerifyPhoneSignupView,
)
from accounts.forms.phones import AddPhoneForm
from accounts.models import PhoneNumber, User
from accounts.services.phones import (
    add_phone,
    remove_phone,
    set_phone,
    set_primary_phone,
)
from accounts.services.phone_flows import PhoneVerificationProcess
from accounts.services.phone_proofs import (
    VERIFY_PURPOSE,
    bind_phone_proof,
    proof_contact,
)


def _require_gateway():
    """Also enforce delivery policy on requests resumed directly after reauthentication."""
    if not settings.PHONE_LOGIN_ENABLED:
        raise Http404()


@login_required
@require_http_methods(["GET", "POST"])
def phone_numbers(request):
    """List contacts even when Gateway is disabled, and accept additions via POST."""
    form = AddPhoneForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        return _add_phone(request, form)
    return _render_phones(request, form)


def _render_phones(request, form):
    """Render server-owned contact data and the configured enrollment limit."""
    contacts = list(request.user.phone_numbers.all())
    return render(
        request,
        "accounts/phones.html",
        {
            "form": form,
            "phone_numbers": contacts,
            "phone_limit": settings.AUTH_MAX_PHONE_NUMBERS,
            "phone_limit_reached": len(contacts) >= settings.AUTH_MAX_PHONE_NUMBERS,
            "verified_phone_count": sum(contact.verified for contact in contacts),
            "phone_login_mode": settings.AUTH_PHONE_LOGIN_MODE,
        },
    )


@reauthentication_required
@rate_limit(action="change_phone")
def _add_phone(request, form):
    """Keep a pending contact after delivery failure so the user can retry or remove it."""
    _require_gateway()
    if form.is_valid():
        try:
            contact = add_phone(request.user, form.cleaned_data["phone"])
        except ValidationError as exc:
            form.add_error("phone", exc)
        else:
            # The pending record is already committed so delivery failures keep it.
            # Recheck under a lock before sending if another session removed it.
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                contact = get_object_or_404(PhoneNumber, pk=contact.pk, user=user)
                PhoneVerificationProcess.initiate_for_contact(request, contact)
            return redirect("account_verify_phone")
    return _render_phones(request, form)


@login_required
@require_POST
@reauthentication_required
@rate_limit(action="change_phone")
def verify_phone_contact(request, pk):
    """Start verification only for the authenticated owner's pending contact."""
    _require_gateway()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        contact = get_object_or_404(PhoneNumber, pk=pk, user=user)
        if contact.verified:
            messages.info(request, "Номер уже подтверждён.")
            return redirect("account_change_phone")
        PhoneVerificationProcess.initiate_for_contact(request, contact)
    return redirect("account_verify_phone")


@login_required
@require_POST
@reauthentication_required
def primary_phone(request, pk):
    """Set the primary contact with a UUID scoped to the current account."""
    return _change_contact(request, pk, set_primary_phone, "Основной номер изменён.")


@login_required
@require_POST
@reauthentication_required
def delete_phone(request, pk):
    """Delete one contact without leaving the account without a usable login."""
    return _change_contact(request, pk, remove_phone, "Номер удалён.")


def _change_contact(request, pk, operation, success_message):
    """Present domain validation errors without exposing another account's contacts."""
    try:
        operation(request.user, pk)
    except PhoneNumber.DoesNotExist:
        raise Http404() from None
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)
    else:
        messages.success(request, success_message)
    return redirect("account_change_phone")


class PhoneProofMixin:
    """Validate native verification state before reading or changing a contact."""

    def _expired(self):
        """Invalidate legacy or removed contact proofs with a recoverable message."""
        self.process.abort()
        messages.error(self.request, "Проверка номера устарела. Запросите новый код.")
        if hasattr(self, "stage"):
            return self.stage.abort()
        return redirect("account_change_phone")

    def _contact(self, *, lock=False):
        """Resolve only the exact pending UUID bound when the code was sent."""
        user = self.process.user
        if user is None:
            return None
        if lock:
            user = User.objects.select_for_update().filter(pk=user.pk).first()
        if user is None or not user.is_active:
            return None
        self.process._user = user
        contact = proof_contact(self.process.state, user.pk, VERIFY_PURPOSE, lock=lock)
        return contact if contact is not None and not contact.verified else None

    def get(self, request, *args, **kwargs):
        """Reject stale verification URLs before presenting their code form."""
        if self.process.user and not self._contact():
            return self._expired()
        return super().get(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Hold ownership through native validation, resend and verification finish."""
        _require_gateway()
        if self.process.user and not self._contact(lock=True):
            return self._expired()
        if request.POST.get("action") == "cancel":
            self.process.abort()
            return (
                self.stage.abort()
                if hasattr(self, "stage")
                else redirect("account_change_phone")
            )
        return super().post(request, *args, **kwargs)


class VerifyAddedPhoneView(PhoneProofMixin, _VerifyPhoneChangeView):
    """Reuse allauth's OTP form while supporting bound contacts and resends."""

    def dispatch(self, request, *args, **kwargs):
        """Resume only the current authenticated browser's verification process."""
        state = request.session.get("account_phone_verification")
        self.process = PhoneVerificationProcess(request, state) if state else None
        if self.process:
            self.process = self.process.abort_if_invalid()
        if self.process is None:
            return redirect("account_change_phone")
        return _BaseVerifyPhoneView.dispatch(self, request, *args, **kwargs)


class VerifySignupPhoneView(PhoneProofMixin, _VerifyPhoneSignupView):
    """Keep the native staged-signup gate and add UUID ownership checks."""

    def _change_form_valid(self, form):
        """Bind a changed signup contact before native code replacement and delivery."""
        try:
            contact = set_phone(self.process.user, form.cleaned_data["phone"], False)
        except ValidationError as exc:
            form.add_error("phone", exc)
            return self._change_form_invalid(form)
        bind_phone_proof(self.process.state, contact, VERIFY_PURPOSE)
        return super()._change_form_valid(form)


@login_not_required
@require_http_methods(["GET", "POST"])
def verify_phone(request):
    """Route the existing verification URL to the matching allauth context."""
    _require_gateway()
    view = (
        VerifyAddedPhoneView if request.user.is_authenticated else VerifySignupPhoneView
    )
    return view.as_view()(request)
