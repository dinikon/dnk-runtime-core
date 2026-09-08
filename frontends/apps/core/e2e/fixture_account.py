"""Only create/remove the explicitly marked local Core browser-test account."""

import json
import os

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
if operation not in {"setup", "cleanup"}:
    raise RuntimeError("Unsupported fixture operation.")

User = get_user_model()
with transaction.atomic():
    user = User.objects.select_for_update().filter(username=username).first()
    if user:
        if user.email != email or user.first_name != "Core E2E Fixture":
            raise RuntimeError("Refusing to modify an account without the E2E identity marker.")
        for session in UserSession.objects.filter(user=user):
            session.end()
        user.delete()
    if operation == "setup":
        if EmailAddress.objects.filter(email__iexact=email).exists():
            raise RuntimeError("The fixture email belongs to another account.")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=os.environ["CORE_E2E_PASSWORD"],
            first_name="Core E2E Fixture",
        )
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)

print(json.dumps({"fixture": username, "operation": operation, "ok": True}))
