"""Primary-key policy for application-owned CORE models."""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Give application records stable UUIDv4 identities before persistence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        """Share the field without creating a separate database table."""

        abstract = True
