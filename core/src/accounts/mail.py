"""SMTP with an explicit development-only certificate compatibility option."""

import ssl

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend
from django.utils.functional import cached_property


class SMTPEmailBackend(DjangoSMTPBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify_certificate = settings.EMAIL_VERIFY_CERTIFICATE
        if not self.verify_certificate:
            if not settings.DEBUG:
                raise ImproperlyConfigured(
                    "Unverified SMTP certificates are allowed only with CORE_DEBUG=true."
                )
            if not (self.use_tls or self.use_ssl):
                raise ImproperlyConfigured(
                    "SMTP compatibility mode requires STARTTLS or implicit TLS."
                )

    @cached_property
    def ssl_context(self):
        context = super().ssl_context
        if not self.verify_certificate:
            # Mirrors stdlib smtplib's legacy default, without plaintext fallback.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context
