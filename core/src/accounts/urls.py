from django.urls import path

from . import views

urlpatterns = [
    path("", views.account_overview, name="core_account_overview"),
    path(
        "login/code/confirm/",
        views.ConfirmLoginCodeView.as_view(),
        name="account_confirm_login_code",
    ),
    path(
        "reauthenticate/email/",
        views.EmailReauthenticationView.as_view(),
        name="core_email_reauthenticate",
    ),
    path("sessions/<int:pk>/revoke/", views.revoke_session, name="core_revoke_session"),
    path("2fa/webauthn/add/", views.AddPasskeyView.as_view(), name="mfa_add_webauthn"),
    path(
        "2fa/webauthn/login/",
        views.LoginPasskeyView.as_view(),
        name="mfa_login_webauthn",
    ),
]
