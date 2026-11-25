from django.db import models


class CreationReceipt(models.Model):
    """Bind a successfully used preview nonce to the saved record."""

    id = models.UUIDField(primary_key=True, editable=False)
    object_id = models.PositiveBigIntegerField(null=True)
