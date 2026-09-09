"""Input for adding a contact without changing existing phone ownership."""

from django import forms
from allauth.account.adapter import get_adapter


class AddPhoneForm(forms.Form):
    """Use the same E.164 validation and accessible phone control as allauth."""

    def __init__(self, *args, **kwargs):
        """Build the field through the configured account adapter."""
        super().__init__(*args, **kwargs)
        self.fields["phone"] = get_adapter().phone_form_field(
            required=True, label="Номер телефона"
        )
        self.fields["phone"].widget.attrs.update(
            autocomplete="tel", placeholder="+380501234567"
        )
