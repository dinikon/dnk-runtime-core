"""Shared personal-name inputs for account creation and owner profile editing."""

from django import forms
from accounts.models import User


class ProfileFields(forms.Form):
    """Require given and family names without imposing uniqueness or ASCII rules."""

    last_name = forms.CharField(
        label="Фамилия",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    first_name = forms.CharField(
        label="Имя",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    middle_name = forms.CharField(
        label="Отчество",
        max_length=150,
        required=False,
        help_text="Необязательно",
        widget=forms.TextInput(attrs={"autocomplete": "additional-name"}),
    )


class ProfileForm(ProfileFields, forms.ModelForm):
    """Validate only editable names; identity and security fields are never bound."""

    class Meta:
        """Explicitly limit profile input to the three personal-name fields."""

        model = User
        fields = ("last_name", "first_name", "middle_name")
