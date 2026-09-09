"""Authenticated profile editing through standard Django forms and CSRF."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from accounts.forms import ProfileForm
from accounts.services.profile import update_profile


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def profile(request):
    """Edit only the current user's names, retaining bound values on validation errors."""
    form = ProfileForm(
        request.POST if request.method == "POST" else None, instance=request.user
    )
    if request.method == "POST" and form.is_valid():
        update_profile(request.user, **form.cleaned_data)
        messages.success(request, "Данные профиля сохранены.")
        return redirect("core_profile")
    return render(request, "accounts/profile.html", {"form": form})
