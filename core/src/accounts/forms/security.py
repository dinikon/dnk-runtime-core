"""Sensitive account action forms and recovery inputs."""

from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from allauth.core.exceptions import ImmediateHttpResponse
from django.db import transaction
from accounts.models import User
from accounts.presentation.social_accounts import social_account_label
from accounts.services.capabilities import require_primary_login
from allauth.socialaccount.forms import DisconnectForm as AllauthDisconnectForm


class EmailReauthenticationForm(forms.Form):
    """Accept a six-digit email proof for a suspended security action."""

    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        label="Код из email",
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}
        ),
    )


class DisconnectForm(AllauthDisconnectForm):
    """Reject provider removal that would remove the final enabled login method."""

    def __init__(self, *args, **kwargs):
        """Initialize the native component and apply CORE field or provider metadata."""
        super().__init__(*args, **kwargs)
        self.fields["account"].label = "Подключённый аккаунт"
        self.fields["account"].label_from_instance = social_account_label

    def clean(self):
        """Count only enabled primary methods before disconnecting a provider."""
        from allauth.socialaccount.adapter import get_adapter

        cleaned = forms.Form.clean(self)
        account = cleaned.get("account")
        if account:
            require_primary_login(self.request.user, exclude_social=account.pk)
            get_adapter().validate_disconnect(account, self.accounts)
        return cleaned

    @transaction.atomic
    def save(self):
        """Recheck under the same account lock used by other primary-method removals."""
        user = User.objects.select_for_update().get(pk=self.request.user.pk)
        try:
            require_primary_login(user, exclude_social=self.cleaned_data["account"].pk)
        except forms.ValidationError as exc:
            messages.error(self.request, exc.messages[0])
            raise ImmediateHttpResponse(redirect("socialaccount_connections")) from None
        return super().save()
