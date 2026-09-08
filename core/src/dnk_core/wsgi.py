"""WSGI entrypoint for the standalone Core project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dnk_core.settings")

application = get_wsgi_application()
