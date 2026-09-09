"""Same-origin Core API and server-rendered account/security pages."""

from django.contrib import admin
from django.urls import include, path
from allauth.account.decorators import secure_admin_login

from . import api

admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = [
    path("api/capabilities/", api.capabilities, name="core_api_capabilities"),
    path("api/session/", api.session, name="core_api_session"),
    path("api/me/", api.me, name="core_api_me"),
    # Overrides precede allauth's identical paths; the normal flow is retained.
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]
