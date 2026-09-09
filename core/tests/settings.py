"""Fast isolated test database; production schema isolation is tested separately."""

import os

os.environ["CORE_ENV_FILE"] = ""
os.environ["CORE_AUTH_PASSWORD_MODE"] = "required"
# Existing regression cases retain legacy username login; profile tests cover generated mode.
os.environ["CORE_AUTH_USERNAME_MODE"] = "required"
os.environ["CORE_DEBUG"] = "true"
os.environ["CORE_SECRET_KEY"] = "core-tests-only-not-a-deployment-secret"
os.environ["CORE_PUBLIC_ORIGIN"] = "https://testserver"
os.environ["CORE_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["CORE_TELEGRAM_GATEWAY_ENABLED"] = "true"
os.environ["CORE_TELEGRAM_GATEWAY_TOKEN"] = "core-tests-only-telegram-token"
os.environ["CORE_GOOGLE_CLIENT_ID"] = "test-google-id"
os.environ["CORE_GOOGLE_CLIENT_SECRET"] = "test-google-secret"
os.environ["CORE_GITHUB_CLIENT_ID"] = "test-github-id"
os.environ["CORE_GITHUB_CLIENT_SECRET"] = "test-github-secret"

from dnk_core.settings import *  # noqa: E402,F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
