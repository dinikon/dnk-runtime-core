"""Present recovery-code setup without changing allauth's security lifecycle."""

from django.http import Http404
from django.views.generic import TemplateView
from allauth.mfa.recovery_codes.internal.flows import can_generate_recovery_codes
from allauth.mfa.recovery_codes.views import ViewRecoveryCodesView


class RecoveryCodesView(ViewRecoveryCodesView):
    """Show setup guidance when the current account has no recovery codes yet."""

    empty_template_name = "accounts/recovery_codes_empty.html"

    def get_context_data(self, **kwargs):
        """Keep native one-time display and handle only its missing-record response."""
        try:
            return super().get_context_data(**kwargs)
        except Http404:
            # Upstream raises Http404 when view_recovery_codes finds no record.
            # Generation remains on its authenticated, CSRF-protected POST view.
            self.is_empty = True
            context = TemplateView.get_context_data(self, **kwargs)
            context["can_generate_codes"] = can_generate_recovery_codes(
                self.request.user
            )
            return context

    def get_template_names(self):
        """Render the setup state without mounting scripts for nonexistent codes."""
        if getattr(self, "is_empty", False):
            return [self.empty_template_name]
        return super().get_template_names()
