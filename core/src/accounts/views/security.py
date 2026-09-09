"""Account summary and owner-scoped session management."""

from django.contrib import messages
from django.db import transaction
from allauth.account.views import EmailView as AllauthEmailView
from accounts.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from allauth.account.decorators import reauthentication_required
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled
from allauth.socialaccount.models import SocialAccount
from allauth.usersessions.internal.flows.sessions import end_sessions
from allauth.usersessions.models import UserSession


@login_required
@never_cache
def account_overview(request):
    """Render current account contacts, authenticators and active sessions."""
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
    """End an owned session after CSRF and recent authentication checks."""
    session = get_object_or_404(UserSession, pk=pk, user=request.user)
    was_current = session.is_current()
    end_sessions(request, [session])
    if was_current:
        return redirect("/")
    messages.success(request, "Сессия завершена.")
    return redirect("usersessions_list")


class EmailView(AllauthEmailView):
    """Keep native email management while serializing primary-method removals."""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Hold the account lock across the adapter check and native email deletion."""
        request.user = User.objects.select_for_update().get(pk=request.user.pk)
        return super().post(request, *args, **kwargs)
