"""Only create/remove the explicitly marked local Core browser-test account."""

import json
import os
import re
from pathlib import Path
from email import policy
from email.parser import Parser

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from allauth.account.models import EmailAddress
from allauth.usersessions.models import UserSession

if not settings.DEBUG:
    raise RuntimeError("Browser fixtures are limited to DEBUG development settings.")

username = "core_e2e_qa"
email = "core_e2e_qa@example.invalid"
operation = os.environ["CORE_E2E_OPERATION"]
if operation not in {
    "setup",
    "cleanup",
    "mail",
    "login-mail",
    "reset",
    "navigation",
    "inspect",
}:
    raise RuntimeError("Unsupported fixture operation.")

if settings.EMAIL_BACKEND not in {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
}:
    raise RuntimeError(
        "Browser fixtures require isolated email delivery; SMTP is forbidden."
    )
signup_username = os.environ.get("CORE_E2E_SIGNUP_USERNAME", "")
if not re.fullmatch(r"core_e2e_passkey_[a-f0-9]{12}", signup_username):
    raise RuntimeError("Expected a unique, marked passkey signup fixture.")
signup_email = signup_username + "@example.invalid"

if operation in {"mail", "login-mail"}:
    if settings.EMAIL_BACKEND != "django.core.mail.backends.filebased.EmailBackend":
        raise RuntimeError(
            "Browser code verification requires the isolated file email backend."
        )
    messages = sorted(
        Path(settings.EMAIL_FILE_PATH).glob("*.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in messages:
        message = Parser(policy=policy.default).parsestr(path.read_text())
        if message.get("To") == (email if operation == "login-mail" else signup_email):
            match = re.search(
                r"\b[0-9]{6}\b",
                (
                    message.get_body(preferencelist=("plain",)).get_content()
                    if message.is_multipart()
                    else message.get_content()
                ),
            )
            if match:
                print(json.dumps({"code": match.group()}))
                break
    else:
        raise RuntimeError("No verification code for the marked browser fixture.")
elif operation in {"navigation", "inspect"}:
    from allauth.mfa.models import Authenticator
    from allauth.socialaccount.models import SocialAccount

    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(username=username)
        if user.email != email or user.first_name != "Core E2E Fixture":
            raise RuntimeError("Refusing to modify an unmarked browser account.")
        if operation == "navigation":
            role = os.environ.get("CORE_E2E_ROLE", "member")
            if role not in {"member", "staff", "superuser"}:
                raise RuntimeError("Unsupported browser fixture role.")
            # The superuser-only case exercises the UI's staff OR superuser rule.
            # Django admin keeps its own is_staff authorization requirement.
            user.is_staff = role == "staff"
            user.is_superuser = role == "superuser"
            user.save(update_fields=["is_staff", "is_superuser"])
            profiles = {
                "github": {"login": "core_qa_github"},
                "telegram": {"preferred_username": "core_qa_telegram"},
                "google": {"email": "core_qa_google@example.invalid"},
            }
            for provider, extra_data in profiles.items():
                SocialAccount.objects.get_or_create(
                    user=user,
                    provider=provider,
                    uid=f"core-e2e-{provider}-{user.pk}",
                    defaults={"extra_data": extra_data},
                )
        print(
            json.dumps(
                {
                    "fixture": username,
                    "operation": operation,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "recovery_authenticators": Authenticator.objects.filter(
                        user=user, type=Authenticator.Type.RECOVERY_CODES
                    ).count(),
                }
            )
        )
else:
    User = get_user_model()
    with transaction.atomic():
        user = User.objects.select_for_update().filter(username=username).first()
        if user:
            if user.email != email or user.first_name != "Core E2E Fixture":
                raise RuntimeError(
                    "Refusing to modify an account without the E2E identity marker."
                )
            for session in UserSession.objects.filter(user=user):
                session.end()
            user.delete()
        if operation in {"setup", "reset"}:
            if EmailAddress.objects.filter(email__iexact=email).exists():
                raise RuntimeError("The fixture email belongs to another account.")
            user = User.objects.create_user(
                username=username,
                email=email,
                password=os.environ["CORE_E2E_PASSWORD"],
                first_name="Core E2E Fixture",
            )
            EmailAddress.objects.create(
                user=user, email=email, verified=True, primary=True
            )

    if operation == "setup":
        if (
            User.objects.filter(username=signup_username).exists()
            or EmailAddress.objects.filter(email__iexact=signup_email).exists()
        ):
            raise RuntimeError("Signup fixture already exists.")
    elif operation == "cleanup":
        staged = User.objects.filter(username=signup_username).first()
        if staged:
            if staged.email != signup_email:
                raise RuntimeError("Refusing to delete an unmarked signup account.")
            for session in UserSession.objects.filter(user=staged):
                session.end()
            staged.delete()
    print(json.dumps({"fixture": username, "operation": operation, "ok": True}))
